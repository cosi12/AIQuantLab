from __future__ import annotations

import pytest

from aiquantlab.data.exceptions import DataContractError, DatasetIntegrityError
from aiquantlab.data.models import DatasetMetadata, Timeframe
from aiquantlab.data.quality import DataQualityReport, ValidationOptions, validate_ohlcv
from aiquantlab.data.storage import read_processed_dataset, write_processed_dataset


def test_processed_dataset_round_trip_with_integrity_check(canonical_frame, tmp_path) -> None:
    output = tmp_path / "xauusd-15m.parquet"
    report = validate_ohlcv(canonical_frame, ValidationOptions(timeframe=Timeframe.M15))
    metadata = DatasetMetadata(symbol="XAUUSD", source="test-vendor", timeframe=Timeframe.M15)

    written_manifest = write_processed_dataset(
        canonical_frame,
        output,
        metadata=metadata,
        quality_report=report,
    )
    loaded, loaded_manifest = read_processed_dataset(output)

    assert loaded.equals(canonical_frame)
    assert loaded_manifest.sha256 == written_manifest.sha256
    assert loaded_manifest.metadata.symbol == "XAUUSD"


def test_processed_dataset_detects_changed_file(canonical_frame, tmp_path) -> None:
    output = tmp_path / "xauusd-15m.parquet"
    report = validate_ohlcv(canonical_frame, ValidationOptions(timeframe=Timeframe.M15))
    metadata = DatasetMetadata(symbol="XAUUSD", source="test-vendor", timeframe=Timeframe.M15)
    write_processed_dataset(
        canonical_frame,
        output,
        metadata=metadata,
        quality_report=report,
    )
    with output.open("ab") as handle:
        handle.write(b"changed")

    with pytest.raises(DatasetIntegrityError, match="checksum"):
        read_processed_dataset(output)


def test_invalid_dataset_is_not_persisted(canonical_frame, tmp_path) -> None:
    output = tmp_path / "invalid.parquet"
    invalid_report = DataQualityReport(
        passed=False,
        row_count=len(canonical_frame),
    )
    metadata = DatasetMetadata(symbol="XAUUSD", source="test-vendor", timeframe=Timeframe.M15)

    with pytest.raises(DataContractError, match="quality errors"):
        write_processed_dataset(
            canonical_frame,
            output,
            metadata=metadata,
            quality_report=invalid_report,
        )

    assert not output.exists()

