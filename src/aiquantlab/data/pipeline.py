"""Small, composable orchestration for one ingestion run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from aiquantlab.data.loading import DataSourceConfig, load_market_csv
from aiquantlab.data.models import DatasetMetadata
from aiquantlab.data.quality import DataQualityReport, ValidationOptions, validate_ohlcv


@dataclass(frozen=True, slots=True)
class IngestionResult:
    frame: pd.DataFrame
    metadata: DatasetMetadata
    quality_report: DataQualityReport


def ingest_csv(path: str | Path, config: DataSourceConfig) -> IngestionResult:
    """Load and validate one CSV without mutating or persisting the source."""

    frame = load_market_csv(path, config)
    metadata = config.metadata()
    report = validate_ohlcv(
        frame,
        ValidationOptions(
            timeframe=config.timeframe,
            calendar_policy=config.calendar_policy,
        ),
    )
    return IngestionResult(frame=frame, metadata=metadata, quality_report=report)

