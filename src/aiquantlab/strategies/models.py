"""Immutable definitions for strategy candidates, not deployment instructions."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aiquantlab.data.models import Timeframe
from aiquantlab.research.models import EventDefinition


class StrategyDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class ExecutionTiming(StrEnum):
    NEXT_BAR_OPEN = "next_bar_open"


class PositionSizingMethod(StrEnum):
    FIXED_FRACTION_NOTIONAL = "fixed_fraction_notional"


class CandidatePurpose(StrEnum):
    QUALIFICATION = "qualification"
    PIPELINE_PROBE = "pipeline_probe"


class PositionSizingRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    method: PositionSizingMethod = PositionSizingMethod.FIXED_FRACTION_NOTIONAL
    fraction: float = Field(gt=0.0, le=1.0)


class StrategyRiskRules(BaseModel):
    """Risk choices are explicit even when intrabar exits are intentionally disabled."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    maximum_concurrent_positions: int = Field(default=1, ge=1, le=1)
    stop_loss_fraction: float | None = Field(default=None, gt=0.0, lt=1.0)
    take_profit_fraction: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def reject_ambiguous_intrabar_rules(self) -> Self:
        if self.stop_loss_fraction is not None or self.take_profit_fraction is not None:
            raise ValueError(
                "the reference bar engine does not support intrabar stop-loss or take-profit rules"
            )
        return self


class StrategyCandidate(BaseModel):
    """A complete, frozen rule set eligible for historical validation only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    candidate_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,63}$")
    revision: int = Field(default=1, ge=1)
    title: str = Field(min_length=3)
    source_finding_id: str = Field(min_length=3)
    source_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    research_gate_passed: bool
    purpose: CandidatePurpose
    symbol: str = Field(min_length=1)
    timeframe: Timeframe
    direction: StrategyDirection
    entry_event: EventDefinition
    signal_semantics: str = "evaluate after the signal bar has fully closed"
    execution_timing: ExecutionTiming = ExecutionTiming.NEXT_BAR_OPEN
    holding_bars: int = Field(ge=1)
    position_sizing: PositionSizingRule
    risk_rules: StrategyRiskRules = Field(default_factory=StrategyRiskRules)
    assumptions: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def qualification_requires_research_gate(self) -> Self:
        if self.purpose == CandidatePurpose.QUALIFICATION and not self.research_gate_passed:
            raise ValueError("qualification candidates must pass the research gate")
        if self.purpose == CandidatePurpose.PIPELINE_PROBE and self.research_gate_passed:
            raise ValueError("pipeline probes must not claim to pass the research gate")
        return self

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("assumptions")
    @classmethod
    def assumptions_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("assumptions must be unique")
        return value

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
