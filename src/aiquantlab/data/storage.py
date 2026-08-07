"""Integrity-checked persistence for canonical processed datasets."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from aiquantlab.data.exceptions import DataContractError, DatasetIntegrityError
from aiquantlab.data.models import DatasetMetadata
from aiquantlab.data.quality import DataQualityReport
from aiquantlab.data.schema import OHLCV_COLUMNS


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 2
    data_file: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    row_count: int = Field(ge=0)
    columns: tuple[str, ...] = ()
    metadata: DatasetMetadata
    quality_report: DataQualityReport
    created_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())


def manifest_path_for(data_path: str | Path) -> Path:
    path = Path(data_path)
    return path.with_suffix(path.suffix + ".manifest.json")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_processed_dataset(
    frame: pd.DataFrame,
    path: str | Path,
    *,
    metadata: DatasetMetadata,
    quality_report: DataQualityReport,
    overwrite: bool = False,
    require_valid: bool = True,
) -> DatasetManifest:
    """Write Parquet plus a provenance manifest, using same-directory temp files."""

    output_path = Path(path)
    if output_path.suffix.lower() != ".parquet":
        raise DataContractError("processed datasets must use a .parquet extension")
    missing_columns = sorted(set(OHLCV_COLUMNS).difference(frame.columns))
    if missing_columns:
        raise DataContractError(f"cannot persist dataset without columns: {missing_columns}")
    if require_valid and not quality_report.passed:
        raise DataContractError("refusing to persist a dataset with quality errors")
    if quality_report.row_count != len(frame):
        raise DataContractError("quality report row count does not match the dataset")

    sidecar_path = manifest_path_for(output_path)
    if not overwrite and (output_path.exists() or sidecar_path.exists()):
        raise FileExistsError(f"dataset or manifest already exists: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    temporary_data = output_path.with_name(f".{output_path.stem}.{token}.tmp.parquet")
    temporary_manifest = sidecar_path.with_name(f".{sidecar_path.name}.{token}.tmp")

    try:
        frame.to_parquet(
            temporary_data,
            index=False,
            engine="pyarrow",
        )
        manifest = DatasetManifest(
            data_file=output_path.name,
            sha256=file_sha256(temporary_data),
            row_count=len(frame),
            columns=tuple(str(column) for column in frame.columns),
            metadata=metadata,
            quality_report=quality_report,
        )
        temporary_manifest.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temporary_data.replace(output_path)
        temporary_manifest.replace(sidecar_path)
    finally:
        temporary_data.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
    return manifest


def read_processed_dataset(
    path: str | Path,
    *,
    verify_integrity: bool = True,
) -> tuple[pd.DataFrame, DatasetManifest]:
    """Read a processed dataset and verify its checksum and manifest contract."""

    data_path = Path(path)
    sidecar_path = manifest_path_for(data_path)
    if not data_path.is_file():
        raise FileNotFoundError(data_path)
    if not sidecar_path.is_file():
        raise DatasetIntegrityError(f"dataset manifest is missing: {sidecar_path}")

    manifest = DatasetManifest.model_validate_json(sidecar_path.read_text(encoding="utf-8"))
    if manifest.data_file != data_path.name:
        raise DatasetIntegrityError("manifest references a different data file")
    if verify_integrity and file_sha256(data_path) != manifest.sha256:
        raise DatasetIntegrityError("processed dataset checksum does not match its manifest")

    frame = pd.read_parquet(data_path, engine="pyarrow")
    missing_columns = sorted(set(OHLCV_COLUMNS).difference(frame.columns))
    if missing_columns:
        raise DatasetIntegrityError(f"processed dataset is missing columns: {missing_columns}")
    if len(frame) != manifest.row_count:
        raise DatasetIntegrityError("processed dataset row count does not match its manifest")
    if manifest.columns and tuple(str(column) for column in frame.columns) != manifest.columns:
        raise DatasetIntegrityError("processed dataset columns do not match its manifest")
    return frame, manifest
