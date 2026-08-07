from __future__ import annotations

import pandas as pd
import pytest

from aiquantlab.data import Timeframe, aggregate_tick_parquet_files
from aiquantlab.data.exceptions import DataContractError


def _ticks() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2024-01-02T00:00:01Z",
                    "2024-01-02T00:04:00Z",
                    "2024-01-02T00:05:00Z",
                    "2024-01-02T00:15:00Z",
                ],
                utc=True,
            ),
            "bid_price": [2000.0, 2001.0, 2002.0, 2003.0],
            "ask_price": [2000.4, 2001.6, 2002.2, 2003.2],
            "bid_volume": [None, None, None, None],
            "ask_volume": [None, None, None, None],
        }
    )


def test_tick_aggregation_preserves_midpoint_and_execution_prices(tmp_path) -> None:
    source = tmp_path / "ticks.parquet"
    _ticks().to_parquet(source, index=False)

    result = aggregate_tick_parquet_files(
        [source],
        timeframe=Timeframe.M5,
        source_root=tmp_path,
    )

    assert result.source.row_count == 4
    assert result.source.file_count == 1
    assert len(result.source.sha256) == 64
    assert result.frame["open"].tolist() == pytest.approx([2000.2, 2002.1, 2003.1])
    assert result.frame["close"].tolist() == pytest.approx([2001.3, 2002.1, 2003.1])
    assert result.frame["volume"].tolist() == [2.0, 1.0, 1.0]
    assert result.frame["ask_open"].tolist() == [2000.4, 2002.2, 2003.2]
    assert result.frame["bid_close"].tolist() == [2001.0, 2002.0, 2003.0]


def test_tick_aggregation_rejects_crossed_quotes(tmp_path) -> None:
    source = tmp_path / "ticks.parquet"
    ticks = _ticks()
    ticks.loc[1, "ask_price"] = 1999.0
    ticks.to_parquet(source, index=False)

    with pytest.raises(DataContractError, match="ask prices below bid"):
        aggregate_tick_parquet_files(
            [source],
            timeframe=Timeframe.M5,
            source_root=tmp_path,
        )
