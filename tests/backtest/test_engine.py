from __future__ import annotations

import pandas as pd
import pytest

from aiquantlab.backtest import ExecutionModel, run_backtest
from aiquantlab.data import Timeframe
from aiquantlab.research.models import (
    ConditionOperator,
    EventCondition,
    EventDefinition,
)
from aiquantlab.strategies import (
    CandidatePurpose,
    PositionSizingRule,
    StrategyCandidate,
    StrategyDirection,
)


def candidate() -> StrategyCandidate:
    return StrategyCandidate(
        candidate_id="XAUUSD-TEST-001",
        title="Causal test candidate",
        source_finding_id="FND-TEST-001",
        source_evidence_sha256="a" * 64,
        research_gate_passed=True,
        purpose=CandidatePurpose.QUALIFICATION,
        symbol="XAUUSD",
        timeframe=Timeframe.M15,
        direction=StrategyDirection.LONG,
        entry_event=EventDefinition(
            name="bullish_bar",
            description="Current closed bar has a positive candle body.",
            conditions=(
                EventCondition(
                    left_column="close",
                    operator=ConditionOperator.GREATER_THAN,
                    right_column="open",
                ),
            ),
        ),
        holding_bars=2,
        position_sizing=PositionSizingRule(fraction=1.0),
        assumptions=("Synthetic test data only.",),
    )


def execution_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=10, freq="15min", tz="UTC")
    opens = pd.Series([100.0 + value for value in range(10)], dtype="float64")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": opens + 1.0,
            "low": opens - 1.0,
            "close": opens + 0.5,
            "volume": 10.0,
            "bid_open": opens - 0.1,
            "ask_open": opens + 0.1,
            "features_valid": True,
        }
    )


def test_backtest_uses_closed_signal_then_next_open_bid_ask_execution() -> None:
    frame = execution_frame()
    result = run_backtest(
        frame,
        candidate(),
        start=frame["timestamp"].iloc[0],
        end=frame["timestamp"].iloc[-1] + pd.Timedelta(minutes=15),
        execution_model=ExecutionModel(slippage_bps_per_side=0.0),
    )

    first = result.trades[0]
    assert first.signal_timestamp == frame["timestamp"].iloc[0].to_pydatetime()
    assert first.entry_timestamp == frame["timestamp"].iloc[1].to_pydatetime()
    assert first.exit_timestamp == frame["timestamp"].iloc[3].to_pydatetime()
    assert first.entry_price == pytest.approx(101.1)
    assert first.exit_price == pytest.approx(102.9)
    assert first.net_return < first.gross_mid_return
    assert result.summary.trade_count == 4


def test_backtest_does_not_carry_positions_across_split_end() -> None:
    frame = execution_frame()
    end = frame["timestamp"].iloc[3]
    result = run_backtest(
        frame,
        candidate(),
        start=frame["timestamp"].iloc[0],
        end=end,
    )

    assert result.summary.trade_count == 0
