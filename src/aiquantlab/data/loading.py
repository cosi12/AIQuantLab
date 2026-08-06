"""Market-data loading and timestamp normalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field

from aiquantlab.data.exceptions import DataContractError
from aiquantlab.data.models import (
    CalendarPolicy,
    CandleTimestampConvention,
    DatasetMetadata,
    PriceBasis,
    Timeframe,
    VolumeType,
)
from aiquantlab.data.schema import NUMERIC_COLUMNS, OHLCV_COLUMNS, TIMESTAMP_COLUMN


class ColumnMapping(BaseModel):
    """Source column names mapped to the canonical OHLCV schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    timestamp: str = "timestamp"
    open: str = "open"
    high: str = "high"
    low: str = "low"
    close: str = "close"
    volume: str = "volume"

    def source_to_canonical(self) -> dict[str, str]:
        return {source: canonical for canonical, source in self.model_dump().items()}


class DataSourceConfig(BaseModel):
    """Validated ingestion configuration for one market-data source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(min_length=1)
    source: str = Field(min_length=1)
    timeframe: Timeframe
    source_timezone: str = "UTC"
    timestamp_convention: CandleTimestampConvention = CandleTimestampConvention.OPEN
    price_basis: PriceBasis = PriceBasis.UNKNOWN
    volume_type: VolumeType = VolumeType.UNKNOWN
    calendar_policy: CalendarPolicy = CalendarPolicy.WEEKDAYS
    column_mapping: ColumnMapping = Field(default_factory=ColumnMapping)
    delimiter: str = ","
    timestamp_format: str | None = None

    def metadata(self) -> DatasetMetadata:
        return DatasetMetadata(
            symbol=self.symbol,
            source=self.source,
            timeframe=self.timeframe,
            source_timezone=self.source_timezone,
            timestamp_convention=self.timestamp_convention,
            price_basis=self.price_basis,
            volume_type=self.volume_type,
            calendar_policy=self.calendar_policy,
        )


def load_data_source_config(path: str | Path) -> DataSourceConfig:
    """Load a YAML source configuration with strict validation."""

    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        payload: Any = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise DataContractError(f"configuration must contain a mapping: {config_path}")
    return DataSourceConfig.model_validate(payload)


def normalize_timestamps(
    values: pd.Series,
    *,
    source_timezone: str,
    timestamp_format: str | None = None,
) -> pd.Series:
    """Parse timestamps and convert them to timezone-aware UTC values."""

    parse_options: dict[str, Any] = {"errors": "coerce"}
    if timestamp_format is not None:
        parse_options["format"] = timestamp_format

    if source_timezone.upper() == "UTC":
        return pd.to_datetime(values, utc=True, **parse_options)

    parsed = pd.to_datetime(values, **parse_options)
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return parsed.dt.tz_convert("UTC")

    try:
        return parsed.dt.tz_localize(
            source_timezone,
            ambiguous="raise",
            nonexistent="raise",
        ).dt.tz_convert("UTC")
    except (TypeError, ValueError) as exc:
        raise DataContractError(
            f"timestamps could not be localized from {source_timezone!r} to UTC"
        ) from exc


def load_market_csv(path: str | Path, config: DataSourceConfig) -> pd.DataFrame:
    """Load a CSV into canonical columns without sorting or deduplicating it."""

    csv_path = Path(path)
    frame = pd.read_csv(csv_path, delimiter=config.delimiter)
    source_columns = config.column_mapping.model_dump()
    missing = sorted(set(source_columns.values()).difference(frame.columns))
    if missing:
        raise DataContractError(f"missing source columns in {csv_path}: {missing}")

    frame = frame.rename(columns=config.column_mapping.source_to_canonical())
    frame = frame.loc[:, list(OHLCV_COLUMNS)].copy()
    frame[TIMESTAMP_COLUMN] = normalize_timestamps(
        frame[TIMESTAMP_COLUMN],
        source_timezone=config.source_timezone,
        timestamp_format=config.timestamp_format,
    )
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame

