"""A small bar-event simulator with causal signal and fill timing."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from aiquantlab.backtest.models import (
    BacktestResult,
    BacktestSummary,
    ExecutionModel,
    SimulatedTrade,
)
from aiquantlab.research.conditions import evaluate_event_definition
from aiquantlab.research.exceptions import ResearchContractError
from aiquantlab.strategies.models import StrategyCandidate, StrategyDirection


def _as_utc_timestamp(value: datetime | pd.Timestamp, *, name: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ResearchContractError(f"{name} must be timezone-aware")
    return timestamp.tz_convert("UTC")


def _execution_columns(
    direction: StrategyDirection,
    execution: ExecutionModel,
) -> tuple[str, str]:
    if direction == StrategyDirection.LONG:
        return execution.long_entry_price_column, execution.long_exit_price_column
    return execution.short_entry_price_column, execution.short_exit_price_column


def _fill_prices(
    raw_entry: float,
    raw_exit: float,
    direction: StrategyDirection,
    slippage_bps: float,
) -> tuple[float, float]:
    fraction = slippage_bps / 10_000.0
    if direction == StrategyDirection.LONG:
        return raw_entry * (1.0 + fraction), raw_exit * (1.0 - fraction)
    return raw_entry * (1.0 - fraction), raw_exit * (1.0 + fraction)


def _trade_return(entry: float, exit_: float, direction: StrategyDirection) -> float:
    if direction == StrategyDirection.LONG:
        return exit_ / entry - 1.0
    return (entry - exit_) / entry


def _summarize(trades: tuple[SimulatedTrade, ...], fraction: float) -> BacktestSummary:
    if not trades:
        return BacktestSummary(
            trade_count=0,
            cumulative_return=0.0,
            maximum_drawdown=0.0,
            total_execution_cost_return=0.0,
        )

    returns = np.asarray([trade.net_return for trade in trades], dtype=np.float64)
    equity: NDArray[np.float64] = np.asarray(
        np.cumprod(1.0 + fraction * returns),
        dtype=np.float64,
    )
    initial = np.asarray([1.0], dtype=np.float64)
    equity_with_initial: NDArray[np.float64] = np.concatenate((initial, equity))
    running_peak: NDArray[np.float64] = np.maximum.accumulate(equity_with_initial)
    drawdowns = 1.0 - equity_with_initial / running_peak
    return BacktestSummary(
        trade_count=len(trades),
        cumulative_return=float(equity[-1] - 1.0),
        mean_trade_return=float(np.mean(returns)),
        median_trade_return=float(np.median(returns)),
        standard_deviation_trade_return=float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0,
        win_rate=float(np.mean(returns > 0.0)),
        maximum_drawdown=float(np.max(drawdowns)),
        total_execution_cost_return=float(
            sum(trade.execution_cost_return for trade in trades)
        ),
    )


def run_backtest(
    frame: pd.DataFrame,
    candidate: StrategyCandidate,
    *,
    start: datetime | pd.Timestamp,
    end: datetime | pd.Timestamp,
    execution_model: ExecutionModel | None = None,
    validity_column: str | None = "features_valid",
) -> BacktestResult:
    """Run frozen rules on [start, end), filling only at subsequent bar opens."""

    execution = execution_model or ExecutionModel()
    start_at = _as_utc_timestamp(start, name="start")
    end_at = _as_utc_timestamp(end, name="end")
    if start_at >= end_at:
        raise ResearchContractError("backtest start must precede end")
    if "timestamp" not in frame:
        raise ResearchContractError("backtest frame is missing timestamp")
    timestamps = frame["timestamp"]
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype) or str(timestamps.dtype.tz) != "UTC":
        raise ResearchContractError("backtest timestamps must be UTC")
    if not timestamps.is_monotonic_increasing or timestamps.duplicated().any():
        raise ResearchContractError("backtest timestamps must be unique and ascending")

    entry_column, exit_column = _execution_columns(candidate.direction, execution)
    required = {"open", entry_column, exit_column}
    if validity_column is not None:
        required.add(validity_column)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ResearchContractError(f"backtest frame is missing columns: {missing}")

    signal_mask = evaluate_event_definition(frame, candidate.entry_event)
    if validity_column is not None:
        signal_mask &= frame[validity_column].fillna(False).astype(bool)

    trades: list[SimulatedTrade] = []
    next_exit_index = -1
    for bar_index in range(1, len(frame)):
        if bar_index < next_exit_index:
            continue
        signal_index = bar_index - 1
        if not bool(signal_mask.iloc[signal_index]):
            continue
        signal_timestamp = pd.Timestamp(timestamps.iloc[signal_index])
        entry_timestamp = pd.Timestamp(timestamps.iloc[bar_index])
        exit_index = bar_index + candidate.holding_bars
        if signal_timestamp < start_at or entry_timestamp < start_at or exit_index >= len(frame):
            continue
        exit_timestamp = pd.Timestamp(timestamps.iloc[exit_index])
        if entry_timestamp >= end_at or exit_timestamp >= end_at:
            continue

        raw_entry = float(frame[entry_column].iloc[bar_index])
        raw_exit = float(frame[exit_column].iloc[exit_index])
        mid_entry = float(frame["open"].iloc[bar_index])
        mid_exit = float(frame["open"].iloc[exit_index])
        prices = (raw_entry, raw_exit, mid_entry, mid_exit)
        if not all(np.isfinite(value) and value > 0.0 for value in prices):
            raise ResearchContractError("backtest encountered an invalid execution price")
        entry_price, exit_price = _fill_prices(
            raw_entry,
            raw_exit,
            candidate.direction,
            execution.slippage_bps_per_side,
        )
        net_return = _trade_return(entry_price, exit_price, candidate.direction)
        gross_return = _trade_return(mid_entry, mid_exit, candidate.direction)
        trades.append(
            SimulatedTrade(
                signal_timestamp=signal_timestamp.to_pydatetime(),
                entry_timestamp=entry_timestamp.to_pydatetime(),
                exit_timestamp=exit_timestamp.to_pydatetime(),
                direction=candidate.direction,
                entry_price=entry_price,
                exit_price=exit_price,
                gross_mid_return=gross_return,
                net_return=net_return,
                execution_cost_return=max(0.0, gross_return - net_return),
                holding_bars=candidate.holding_bars,
            )
        )
        next_exit_index = exit_index

    immutable_trades = tuple(trades)
    return BacktestResult(
        candidate_sha256=candidate.fingerprint(),
        start=start_at.to_pydatetime(),
        end=end_at.to_pydatetime(),
        execution_model=execution,
        summary=_summarize(immutable_trades, candidate.position_sizing.fraction),
        trades=immutable_trades,
    )
