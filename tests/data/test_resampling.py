from __future__ import annotations

import pytest

from aiquantlab.data.exceptions import DataContractError
from aiquantlab.data.models import Timeframe
from aiquantlab.data.resampling import resample_ohlcv


def test_resample_15m_to_1h_uses_canonical_ohlcv_aggregation(canonical_frame) -> None:
    result = resample_ohlcv(
        canonical_frame,
        source_timeframe=Timeframe.M15,
        target_timeframe=Timeframe.H1,
    )

    assert len(result) == 2
    assert result.loc[0, "open"] == canonical_frame.loc[0, "open"]
    assert result.loc[0, "high"] == canonical_frame.loc[:3, "high"].max()
    assert result.loc[0, "low"] == canonical_frame.loc[:3, "low"].min()
    assert result.loc[0, "close"] == canonical_frame.loc[3, "close"]
    assert result.loc[0, "volume"] == 400.0


def test_resample_drops_only_incomplete_dataset_boundaries(canonical_frame) -> None:
    starts_late = canonical_frame.iloc[1:].reset_index(drop=True)

    result = resample_ohlcv(
        starts_late,
        source_timeframe=Timeframe.M15,
        target_timeframe=Timeframe.H1,
    )

    assert len(result) == 1
    assert result.loc[0, "timestamp"] == canonical_frame.loc[4, "timestamp"]


def test_resample_rejects_duplicate_timestamps(canonical_frame) -> None:
    duplicated = canonical_frame.copy()
    duplicated.loc[1, "timestamp"] = duplicated.loc[0, "timestamp"]

    with pytest.raises(DataContractError, match="unique timestamps"):
        resample_ohlcv(
            duplicated,
            source_timeframe=Timeframe.M15,
            target_timeframe=Timeframe.H1,
        )

