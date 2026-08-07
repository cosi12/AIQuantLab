"""Immutable plans and reports for chronological strategy validation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aiquantlab.backtest.models import BacktestSummary, ExecutionModel


class SplitRole(StrEnum):
    RESEARCH = "research"
    VALIDATION = "validation"
    FINAL_TEST = "final_test"


class CandidateAssessment(StrEnum):
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    INCONCLUSIVE = "inconclusive"


class ChronologicalSplit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    role: SplitRole
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def require_valid_utc_interval(self) -> Self:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("split boundaries must be timezone-aware")
        if self.start >= self.end:
            raise ValueError("split start must precede end")
        return self


class ValidationCriteria(BaseModel):
    """Predeclared acceptance rules; no metric is selected after observing results."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_trades_per_evaluation_split: int = Field(default=30, ge=1)
    require_positive_mean_return: bool = True
    maximum_drawdown_limit: float = Field(default=0.25, gt=0.0, le=1.0)
    stress_slippage_bps_per_side: float = Field(default=1.0, gt=0.0)


class ValidationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    plan_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,63}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_before_validation: bool
    research_gate_passed: bool
    splits: tuple[ChronologicalSplit, ...] = Field(min_length=3)
    primary_execution_model: ExecutionModel
    criteria: ValidationCriteria

    @field_validator("splits")
    @classmethod
    def names_and_roles_must_be_unique(
        cls,
        value: tuple[ChronologicalSplit, ...],
    ) -> tuple[ChronologicalSplit, ...]:
        if len({split.name for split in value}) != len(value):
            raise ValueError("split names must be unique")
        if len({split.role for split in value}) != len(value):
            raise ValueError("split roles must be unique")
        required = {SplitRole.RESEARCH, SplitRole.VALIDATION, SplitRole.FINAL_TEST}
        if {split.role for split in value} != required:
            raise ValueError("plan requires research, validation, and final_test splits")
        return value

    @model_validator(mode="after")
    def splits_must_be_ordered_and_non_overlapping(self) -> Self:
        starts = [split.start for split in self.splits]
        if starts != sorted(starts):
            raise ValueError("splits must be chronological")
        for previous, current in zip(self.splits, self.splits[1:], strict=False):
            if previous.end > current.start:
                raise ValueError("splits must not overlap")
        if not self.frozen_before_validation:
            raise ValueError("candidate must be frozen before validation")
        return self

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class SplitValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    split: ChronologicalSplit
    primary: BacktestSummary
    stress: BacktestSummary
    criteria_passed: bool
    failures: tuple[str, ...] = ()


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    research_gate_passed: bool
    assessment: CandidateAssessment
    split_results: tuple[SplitValidationResult, ...]
    warnings: tuple[str, ...]
    generated_at: datetime
