from __future__ import annotations

import pytest

from aiquantlab.data.models import DatasetMetadata, Timeframe
from aiquantlab.data.quality import ValidationOptions, validate_ohlcv
from aiquantlab.data.storage import file_sha256, write_processed_dataset
from aiquantlab.features import (
    FEATURE_VALID_COLUMN,
    default_feature_registry,
    materialize_features,
    price_structure_bundle,
    read_materialized_features,
)
from aiquantlab.features.exceptions import FeatureIntegrityError


def test_materialization_writes_checksum_feature_manifest(canonical_frame, tmp_path) -> None:
    source_path = tmp_path / "source.parquet"
    output_path = tmp_path / "features.parquet"
    quality_report = validate_ohlcv(
        canonical_frame,
        ValidationOptions(timeframe=Timeframe.M15),
    )
    source_manifest = write_processed_dataset(
        canonical_frame,
        source_path,
        metadata=DatasetMetadata(
            symbol="XAUUSD",
            source="synthetic-test",
            timeframe=Timeframe.M15,
        ),
        quality_report=quality_report,
    )
    bundle = price_structure_bundle()

    result = materialize_features(
        source_path,
        output_path,
        bundle,
        registry=default_feature_registry(),
        code_version="test-code-version",
    )
    loaded, loaded_manifest = read_materialized_features(output_path)

    assert result.manifest == loaded_manifest
    assert result.manifest.source_ohlcv_sha256 == source_manifest.sha256
    assert result.manifest.feature_bundle_sha256 == bundle.fingerprint()
    assert result.manifest.output_sha256 == file_sha256(output_path)
    assert result.manifest.warm_up_bars == 0
    assert result.manifest.mtf_sources == ()
    assert set(bundle.feature_names).issubset(loaded.columns)
    assert FEATURE_VALID_COLUMN in loaded
    assert loaded[FEATURE_VALID_COLUMN].all()


def test_materialized_checksum_detects_file_change(canonical_frame, tmp_path) -> None:
    source_path = tmp_path / "source.parquet"
    output_path = tmp_path / "features.parquet"
    quality_report = validate_ohlcv(
        canonical_frame,
        ValidationOptions(timeframe=Timeframe.M15),
    )
    write_processed_dataset(
        canonical_frame,
        source_path,
        metadata=DatasetMetadata(
            symbol="XAUUSD",
            source="synthetic-test",
            timeframe=Timeframe.M15,
        ),
        quality_report=quality_report,
    )
    materialize_features(
        source_path,
        output_path,
        price_structure_bundle(),
        registry=default_feature_registry(),
        code_version="test-code-version",
    )
    with output_path.open("ab") as handle:
        handle.write(b"changed")

    with pytest.raises(FeatureIntegrityError, match="checksum"):
        read_materialized_features(output_path)

