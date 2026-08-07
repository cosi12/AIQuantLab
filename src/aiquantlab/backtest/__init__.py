"""Reference event-driven historical execution model."""

from aiquantlab.backtest.engine import run_backtest
from aiquantlab.backtest.models import (
    BacktestResult,
    BacktestSummary,
    ExecutionModel,
    SimulatedTrade,
)

__all__ = [
    "BacktestResult",
    "BacktestSummary",
    "ExecutionModel",
    "SimulatedTrade",
    "run_backtest",
]
