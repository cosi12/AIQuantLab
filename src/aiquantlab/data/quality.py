"""Data-quality checks that avoid silently repairing market data."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Iterable

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from aiquantlab.data.exceptions import DataContractError
from aiquantlab.data.models import CalendarPolicy, Timeframe
from aiquantlab.data.schema import NUMERIC_COLUMNS, OHLCV_COLUMNS, PRICE_COLUMNS


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class QualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    severity: IssueSeverity
    message: str
    count: int = Field(ge=1)
    samples: tuple[str, ...] = ()


class DataQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    row_count: int = Field(ge=0)
    start: datetime | None = None
    end: datetime | None = None
    expected_candle_count: int | None = Field(default=None, ge=0)
    missing_candle_count: int | None = Field(default=None, ge=0)
    issues: tuple[QualityIssue, ...] = ()
    generated_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())

    @property
    def error_count(self) -> int:
        return sum(issue.count for issue in self.issues if issue.severity == IssueSeverity.ERROR)


class ValidationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    timeframe: Timeframe
    calendar_policy: CalendarPolicy = CalendarPolicy.WEEKDAYS
    alignment_offset: timedelta = timedelta(0)
    max_expected_candles: int = Field(default=5_000_000, ge=1)
    sample_size: int = Field(default=5, ge=1, le=100)


def _samples(values: Iterable[object], limit: int) -> tuple[str, ...]:
    return tuple(str(value) for value in list(values)[:limit])


def expected_timestamps(
    timestamps: pd.DatetimeIndex,
    *,
    timeframe: Timeframe,
    calendar_policy: CalendarPolicy,
    max_expected_candles: int = 5_000_000,
) -> pd.DatetimeIndex | None:
    """Build an expected grid, or return None when gap inference is disabled."""

    clean = timestamps.dropna().unique().sort_values()
    if len(clean) == 0 or calendar_policy == CalendarPolicy.OBSERVED_GAPS:
        return None

    span = clean[-1] - clean[0]
    estimated_count = int(span / timeframe.duration) + 1
    if estimated_count > max_expected_candles:
        raise DataContractError(
            f"expected candle grid would contain {estimated_count:,} rows; "
            f"limit is {max_expected_candles:,}"
        )

    expected = pd.date_range(
        start=clean[0],
        end=clean[-1],
        freq=timeframe.pandas_frequency,
    )
    if calendar_policy == CalendarPolicy.WEEKDAYS:
        expected = expected[expected.dayofweek < 5]
    return expected


def find_missing_timestamps(
    timestamps: pd.DatetimeIndex,
    *,
    timeframe: Timeframe,
    calendar_policy: CalendarPolicy,
    max_expected_candles: int = 5_000_000,
) -> pd.DatetimeIndex | None:
    expected = expected_timestamps(
        timestamps,
        timeframe=timeframe,
        calendar_policy=calendar_policy,
        max_expected_candles=max_expected_candles,
    )
    if expected is None:
        return None
    observed = timestamps.dropna().unique()
    return expected.difference(observed)


def validate_ohlcv(frame: pd.DataFrame, options: ValidationOptions) -> DataQualityReport:
    """Validate a canonical OHLCV frame and return all detectable issues."""

    issues: list[QualityIssue] = []
    missing_columns = sorted(set(OHLCV_COLUMNS).difference(frame.columns))
    if missing_columns:
        issue = QualityIssue(
            code="missing_columns",
            severity=IssueSeverity.ERROR,
            message=f"required canonical columns are missing: {missing_columns}",
            count=len(missing_columns),
            samples=tuple(missing_columns[: options.sample_size]),
        )
        return DataQualityReport(passed=False, row_count=len(frame), issues=(issue,))

    timestamps = frame["timestamp"]
    invalid_timestamp_count = int(timestamps.isna().sum())
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype) or str(timestamps.dtype.tz) != "UTC":
        issues.append(
            QualityIssue(
                code="timestamp_not_utc",
                severity=IssueSeverity.ERROR,
                message="timestamp must be timezone-aware datetime64 values in UTC",
                count=max(len(frame), 1),
            )
        )
        timestamp_index = pd.DatetimeIndex([], tz="UTC")
    else:
        timestamp_index = pd.DatetimeIndex(timestamps)

    if invalid_timestamp_count:
        issues.append(
            QualityIssue(
                code="invalid_timestamp",
                severity=IssueSeverity.ERROR,
                message="timestamps contain missing or unparseable values",
                count=invalid_timestamp_count,
            )
        )

    numeric = frame.loc[:, list(NUMERIC_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    non_numeric = numeric.isna() & frame.loc[:, list(NUMERIC_COLUMNS)].notna()
    for column in NUMERIC_COLUMNS:
        count = int(non_numeric[column].sum())
        if count:
            issues.append(
                QualityIssue(
                    code="non_numeric_value",
                    severity=IssueSeverity.ERROR,
                    message=f"{column} contains values that are not numeric",
                    count=count,
                    samples=_samples(frame.loc[non_numeric[column], column], options.sample_size),
                )
            )

    null_counts = frame.loc[:, list(NUMERIC_COLUMNS)].isna().sum()
    for column, raw_count in null_counts.items():
        count = int(raw_count)
        if count:
            issues.append(
                QualityIssue(
                    code="missing_value",
                    severity=IssueSeverity.ERROR,
                    message=f"{column} contains missing values",
                    count=count,
                )
            )

    valid_timestamp_index = timestamp_index.dropna()
    if len(valid_timestamp_index):
        duplicate_mask = timestamps.duplicated(keep=False)
        duplicate_excess = int(timestamps.duplicated(keep="first").sum())
        if duplicate_excess:
            issues.append(
                QualityIssue(
                    code="duplicate_timestamp",
                    severity=IssueSeverity.ERROR,
                    message="multiple candles share the same timestamp",
                    count=duplicate_excess,
                    samples=_samples(
                        timestamps.loc[duplicate_mask].drop_duplicates(), options.sample_size
                    ),
                )
            )

        if not timestamps.dropna().is_monotonic_increasing:
            issues.append(
                QualityIssue(
                    code="timestamp_out_of_order",
                    severity=IssueSeverity.ERROR,
                    message="timestamps must be strictly ascending",
                    count=1,
                )
            )

        # Pandas 3 can preserve microsecond-resolution dtypes, so normalize the
        # integer representation before comparing it with nanosecond timedeltas.
        timestamp_ns = valid_timestamp_index.as_unit("ns").asi8
        misaligned = (
            (timestamp_ns - pd.Timedelta(options.alignment_offset).value)
            % options.timeframe.duration.value
        ) != 0
        misaligned_count = int(np.count_nonzero(misaligned))
        if misaligned_count:
            issues.append(
                QualityIssue(
                    code="timestamp_misaligned",
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"timestamps are not aligned to {options.timeframe.value} with offset "
                        f"{options.alignment_offset}"
                    ),
                    count=misaligned_count,
                    samples=_samples(valid_timestamp_index[misaligned], options.sample_size),
                )
            )

    price_rows = numeric.loc[:, list(PRICE_COLUMNS)].dropna()
    nonpositive_mask = (price_rows <= 0).any(axis=1)
    if int(nonpositive_mask.sum()):
        issues.append(
            QualityIssue(
                code="nonpositive_price",
                severity=IssueSeverity.ERROR,
                message="OHLC prices must be positive",
                count=int(nonpositive_mask.sum()),
                samples=_samples(frame.loc[nonpositive_mask, "timestamp"], options.sample_size),
            )
        )

    invalid_high = price_rows["high"] < price_rows[["open", "close", "low"]].max(axis=1)
    if int(invalid_high.sum()):
        issues.append(
            QualityIssue(
                code="invalid_high",
                severity=IssueSeverity.ERROR,
                message="high must be greater than or equal to open, close, and low",
                count=int(invalid_high.sum()),
                samples=_samples(frame.loc[invalid_high, "timestamp"], options.sample_size),
            )
        )

    invalid_low = price_rows["low"] > price_rows[["open", "close", "high"]].min(axis=1)
    if int(invalid_low.sum()):
        issues.append(
            QualityIssue(
                code="invalid_low",
                severity=IssueSeverity.ERROR,
                message="low must be less than or equal to open, close, and high",
                count=int(invalid_low.sum()),
                samples=_samples(frame.loc[invalid_low, "timestamp"], options.sample_size),
            )
        )

    negative_volume = numeric["volume"].dropna() < 0
    if int(negative_volume.sum()):
        issues.append(
            QualityIssue(
                code="negative_volume",
                severity=IssueSeverity.ERROR,
                message="volume must not be negative",
                count=int(negative_volume.sum()),
                samples=_samples(frame.loc[negative_volume, "timestamp"], options.sample_size),
            )
        )

    expected_count: int | None = None
    missing_count: int | None = None
    if len(valid_timestamp_index):
        expected = expected_timestamps(
            valid_timestamp_index,
            timeframe=options.timeframe,
            calendar_policy=options.calendar_policy,
            max_expected_candles=options.max_expected_candles,
        )
        if expected is not None:
            missing = expected.difference(valid_timestamp_index.unique())
            expected_count = len(expected)
            missing_count = len(missing)
            if missing_count:
                issues.append(
                    QualityIssue(
                        code="missing_candle",
                        severity=IssueSeverity.WARNING,
                        message=(
                            "expected timestamps are absent; confirm the vendor trading session "
                            "before treating all gaps as data loss"
                        ),
                        count=missing_count,
                        samples=_samples(missing, options.sample_size),
                    )
                )

    clean_timestamps = valid_timestamp_index.sort_values()
    start = clean_timestamps[0].to_pydatetime() if len(clean_timestamps) else None
    end = clean_timestamps[-1].to_pydatetime() if len(clean_timestamps) else None
    passed = not any(issue.severity == IssueSeverity.ERROR for issue in issues)
    return DataQualityReport(
        passed=passed,
        row_count=len(frame),
        start=start,
        end=end,
        expected_candle_count=expected_count,
        missing_candle_count=missing_count,
        issues=tuple(issues),
    )
