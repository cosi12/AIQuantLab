"""Causal OHLCV timeframe conversion with explicit candle anchoring."""

from __future__ import annotations

import pandas as pd

from aiquantlab.data.exceptions import DataContractError
from aiquantlab.data.models import Timeframe
from aiquantlab.data.schema import OHLCV_COLUMNS

ZERO_OFFSET = pd.Timedelta(0)


def resample_ohlcv(
    frame: pd.DataFrame,
    *,
    source_timeframe: Timeframe,
    target_timeframe: Timeframe,
    anchor_offset: pd.Timedelta = ZERO_OFFSET,
    drop_boundary_partial: bool = True,
) -> pd.DataFrame:
    """Aggregate open-timestamped bars to a larger, epoch-anchored timeframe."""

    missing_columns = sorted(set(OHLCV_COLUMNS).difference(frame.columns))
    if missing_columns:
        raise DataContractError(f"cannot resample without columns: {missing_columns}")
    if target_timeframe.duration <= source_timeframe.duration:
        raise DataContractError("target timeframe must be larger than source timeframe")
    if target_timeframe.duration % source_timeframe.duration != pd.Timedelta(0):
        raise DataContractError("target timeframe must be an exact multiple of source timeframe")
    timestamps = frame["timestamp"]
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype) or str(timestamps.dtype.tz) != "UTC":
        raise DataContractError("resampling requires timezone-aware UTC timestamps")
    if timestamps.isna().any() or timestamps.duplicated().any():
        raise DataContractError("resampling requires non-null, unique timestamps")
    if not timestamps.is_monotonic_increasing:
        raise DataContractError("resampling requires timestamps in ascending order")
    if frame.empty:
        return frame.loc[:, list(OHLCV_COLUMNS)].copy()

    indexed = frame.set_index("timestamp")
    resampler = indexed.resample(
        target_timeframe.pandas_frequency,
        origin="epoch",
        offset=anchor_offset,
        label="left",
        closed="left",
    )
    result = resampler.agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    groups = resampler["close"].count()
    result = result.loc[groups > 0]

    if drop_boundary_partial and len(result):
        labels_to_drop: list[pd.Timestamp] = []
        first_label = result.index[0]
        first_observation = indexed.index[indexed.index >= first_label][0]
        if first_observation != first_label:
            labels_to_drop.append(first_label)

        last_label = result.index[-1]
        expected_last_observation = (
            last_label + target_timeframe.duration - source_timeframe.duration
        )
        last_observation = indexed.index[indexed.index < last_label + target_timeframe.duration][-1]
        if last_observation != expected_last_observation:
            labels_to_drop.append(last_label)
        if labels_to_drop:
            result = result.drop(index=pd.Index(labels_to_drop).unique(), errors="ignore")

    result.index.name = "timestamp"
    return result.reset_index().loc[:, list(OHLCV_COLUMNS)]
