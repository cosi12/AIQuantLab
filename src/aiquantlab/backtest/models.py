"""Serializable contracts for historical strategy execution."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aiquantlab.strategies.models import StrategyDirection


class ExecutionModel(BaseModel):
    """Observed spread plus explicit adverse slippage at both sides of a trade."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    long_entry_price_column: str = "ask_open"
    long_exit_price_column: str = "bid_open"
    short_entry_price_column: str = "bid_open"
    short_exit_price_column: str = "ask_open"
    slippage_bps_per_side: float = Field(default=0.0, ge=0.0)


class SimulatedTrade(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_timestamp: datetime
    entry_timestamp: datetime
    exit_timestamp: datetime
    direction: StrategyDirection
    entry_price: float = Field(gt=0.0)
    exit_price: float = Field(gt=0.0)
    gross_mid_return: float
    net_return: float
    execution_cost_return: float = Field(ge=0.0)
    holding_bars: int = Field(ge=1)


class BacktestSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_count: int = Field(ge=0)
    cumulative_return: float
    mean_trade_return: float | None = None
    median_trade_return: float | None = None
    standard_deviation_trade_return: float | None = None
    win_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    maximum_drawdown: float = Field(ge=0.0, le=1.0)
    total_execution_cost_return: float = Field(ge=0.0)


class BacktestResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    start: datetime
    end: datetime
    execution_model: ExecutionModel
    summary: BacktestSummary
    trades: tuple[SimulatedTrade, ...]
