"""Typed contracts shared by all market-data components."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

    @property
    def duration(self) -> pd.Timedelta:
        return {
            Timeframe.M1: pd.Timedelta(minutes=1),
            Timeframe.M5: pd.Timedelta(minutes=5),
            Timeframe.M15: pd.Timedelta(minutes=15),
            Timeframe.H1: pd.Timedelta(hours=1),
            Timeframe.H4: pd.Timedelta(hours=4),
            Timeframe.D1: pd.Timedelta(days=1),
        }[self]

    @property
    def pandas_frequency(self) -> str:
        return {
            Timeframe.M1: "1min",
            Timeframe.M5: "5min",
            Timeframe.M15: "15min",
            Timeframe.H1: "1h",
            Timeframe.H4: "4h",
            Timeframe.D1: "1D",
        }[self]


class CandleTimestampConvention(StrEnum):
    OPEN = "open"
    CLOSE = "close"


class PriceBasis(StrEnum):
    BID = "bid"
    ASK = "ask"
    MID = "mid"
    LAST = "last"
    UNKNOWN = "unknown"


class VolumeType(StrEnum):
    TICK = "tick"
    REAL = "real"
    UNKNOWN = "unknown"


class CalendarPolicy(StrEnum):
    CONTINUOUS = "continuous"
    WEEKDAYS = "weekdays"
    OBSERVED_GAPS = "observed_gaps"


class DatasetMetadata(BaseModel):
    """Provenance and interpretation required to use a bar dataset safely."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(min_length=1)
    source: str = Field(min_length=1)
    timeframe: Timeframe
    source_timezone: str = "UTC"
    canonical_timezone: str = "UTC"
    timestamp_convention: CandleTimestampConvention = CandleTimestampConvention.OPEN
    price_basis: PriceBasis = PriceBasis.UNKNOWN
    volume_type: VolumeType = VolumeType.UNKNOWN
    calendar_policy: CalendarPolicy = CalendarPolicy.WEEKDAYS
    notes: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("canonical_timezone")
    @classmethod
    def canonical_data_must_be_utc(cls, value: str) -> str:
        if value.upper() != "UTC":
            raise ValueError("canonical market data must use UTC")
        return "UTC"

