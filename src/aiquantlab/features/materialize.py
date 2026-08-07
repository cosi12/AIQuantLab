"""Apply registered features and publish checksum-verified artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from aiquantlab.data.schema import OHLCV_COLUMNS
from aiquantlab.data.storage import file_sha256, read_processed_dataset
from aiquantlab.features.exceptions import FeatureContractError, FeatureIntegrityError
from aiquantlab.features.models import (
    FeatureBundle,
    FeatureManifest,
    FeatureOutputDType,
    FeatureSpec,
)
from aiquantlab.features.registry import FeatureRegistry


FEATURE_VALID_COLUMN = "features_valid"


@dataclass(frozen=True, slots=True)
class FeatureMaterializationResult:
    frame: pd.DataFrame
    manifest: FeatureManifest
    data_path: Path
    manifest_path: Path


def feature_manifest_path(data_path: str | Path) -> Path:
    path = Path(data_path)
    return path.with_suffix(path.suffix + ".manifest.json")


def _cast_feature_output(series: pd.Series, specification: FeatureSpec) -> pd.Series:
    if specification.output_dtype == FeatureOutputDType.BOOLEAN:
        return series.astype("boolean")

    numeric = pd.to_numeric(series, errors="coerce")
    invalid = series.notna() & numeric.isna()
    if invalid.any():
        raise FeatureContractError(f"feature output is not numeric: {specification.name}")
    return numeric.astype("float64")


def apply_feature_bundle(
    frame: pd.DataFrame,
    bundle: FeatureBundle,
    *,
    registry: FeatureRegistry,
) -> pd.DataFrame:
    """Apply a reviewed bundle without reading future rows or mutating input."""

    missing_ohlcv = sorted(set(OHLCV_COLUMNS).difference(frame.columns))
    if missing_ohlcv:
        raise FeatureContractError(f"feature input is missing OHLCV columns: {missing_ohlcv}")
    output_columns = {*bundle.feature_names, FEATURE_VALID_COLUMN}
    conflicts = sorted(output_columns.intersection(frame.columns))
    if conflicts:
        raise FeatureContractError(f"feature output columns already exist: {conflicts}")
    registry.validate_bundle(bundle)

    materialized = frame.copy()
    validity = pd.Series(True, index=frame.index, dtype="boolean")
    for specification in bundle.features:
        missing_inputs = sorted(set(specification.input_columns).difference(frame.columns))
        if missing_inputs:
            raise FeatureContractError(
                f"feature {specification.name} is missing inputs: {missing_inputs}"
            )
        transform = registry.get_transform(specification)
        output = transform(frame, specification)
        if len(output) != len(frame) or not output.index.equals(frame.index):
            raise FeatureContractError(
                f"feature {specification.name} did not preserve input rows and index"
            )
        output = _cast_feature_output(output, specification).copy()
        if specification.warm_up_bars:
            if specification.output_dtype == FeatureOutputDType.BOOLEAN:
                output.iloc[: specification.warm_up_bars] = pd.NA
            else:
                output.iloc[: specification.warm_up_bars] = np.nan
        output.name = specification.name
        materialized[specification.name] = output
        validity &= output.notna()

    materialized[FEATURE_VALID_COLUMN] = validity
    return materialized


def materialize_features(
    source_path: str | Path,
    output_path: str | Path,
    bundle: FeatureBundle,
    *,
    registry: FeatureRegistry,
    code_version: str,
    overwrite: bool = False,
) -> FeatureMaterializationResult:
    """Load verified OHLCV, materialize a bundle, and atomically publish artifacts."""

    if not code_version.strip():
        raise FeatureContractError("code_version must not be empty")
    source_data_path = Path(source_path)
    destination = Path(output_path)
    if destination.suffix.lower() != ".parquet":
        raise FeatureContractError("feature datasets must use a .parquet extension")
    if source_data_path.resolve() == destination.resolve():
        raise FeatureContractError("feature output must not overwrite source OHLCV")

    source_frame, source_manifest = read_processed_dataset(source_data_path)
    materialized = apply_feature_bundle(source_frame, bundle, registry=registry)
    sidecar = feature_manifest_path(destination)
    if not overwrite and (destination.exists() or sidecar.exists()):
        raise FileExistsError(f"feature dataset or manifest already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    temporary_data = destination.with_name(f".{destination.stem}.{token}.tmp.parquet")
    temporary_manifest = sidecar.with_name(f".{sidecar.name}.{token}.tmp")
    try:
        materialized.to_parquet(temporary_data, index=False, engine="pyarrow")
        manifest = FeatureManifest(
            output_file=destination.name,
            output_sha256=file_sha256(temporary_data),
            row_count=len(materialized),
            source_ohlcv_file=source_data_path.name,
            source_ohlcv_sha256=source_manifest.sha256,
            feature_bundle=bundle,
            feature_bundle_sha256=bundle.fingerprint(),
            feature_columns=bundle.feature_names,
            validity_column=FEATURE_VALID_COLUMN,
            code_version=code_version,
            warm_up_bars=bundle.warm_up_bars,
            created_at=datetime.now(timezone.utc),
        )
        temporary_manifest.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temporary_data.replace(destination)
        temporary_manifest.replace(sidecar)
    finally:
        temporary_data.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
    return FeatureMaterializationResult(
        frame=materialized,
        manifest=manifest,
        data_path=destination,
        manifest_path=sidecar,
    )


def read_materialized_features(
    path: str | Path,
    *,
    verify_integrity: bool = True,
) -> tuple[pd.DataFrame, FeatureManifest]:
    data_path = Path(path)
    sidecar = feature_manifest_path(data_path)
    if not data_path.is_file():
        raise FileNotFoundError(data_path)
    if not sidecar.is_file():
        raise FeatureIntegrityError(f"feature manifest is missing: {sidecar}")

    manifest = FeatureManifest.model_validate_json(sidecar.read_text(encoding="utf-8"))
    if manifest.output_file != data_path.name:
        raise FeatureIntegrityError("feature manifest references a different data file")
    if verify_integrity and file_sha256(data_path) != manifest.output_sha256:
        raise FeatureIntegrityError("feature dataset checksum does not match its manifest")
    frame = pd.read_parquet(data_path, engine="pyarrow")
    required = {*OHLCV_COLUMNS, *manifest.feature_columns, manifest.validity_column}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise FeatureIntegrityError(f"feature dataset is missing columns: {missing}")
    if len(frame) != manifest.row_count:
        raise FeatureIntegrityError("feature dataset row count does not match its manifest")
    return frame, manifest
