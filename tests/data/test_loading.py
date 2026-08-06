from __future__ import annotations

import pandas as pd
import pytest

from aiquantlab.data.exceptions import DataContractError
from aiquantlab.data.loading import ColumnMapping, DataSourceConfig, load_market_csv
from aiquantlab.data.models import Timeframe


def test_load_market_csv_maps_columns_and_converts_local_time_to_utc(tmp_path) -> None:
    source = tmp_path / "bars.csv"
    source.write_text(
        "Date,O,H,L,C,V\n"
        "2024-01-02 08:00:00,2000,2002,1999,2001,10\n",
        encoding="utf-8",
    )
    config = DataSourceConfig(
        symbol="xauusd",
        source="test-vendor",
        timeframe=Timeframe.M15,
        source_timezone="Asia/Shanghai",
        column_mapping=ColumnMapping(
            timestamp="Date",
            open="O",
            high="H",
            low="L",
            close="C",
            volume="V",
        ),
    )

    result = load_market_csv(source, config)

    assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert result.loc[0, "timestamp"] == pd.Timestamp("2024-01-02 00:00:00", tz="UTC")
    assert config.metadata().symbol == "XAUUSD"


def test_load_market_csv_rejects_missing_source_columns(tmp_path) -> None:
    source = tmp_path / "bars.csv"
    source.write_text("timestamp,open,high,low,close\n", encoding="utf-8")
    config = DataSourceConfig(
        symbol="XAUUSD",
        source="test-vendor",
        timeframe=Timeframe.M15,
    )

    with pytest.raises(DataContractError, match="missing source columns"):
        load_market_csv(source, config)

