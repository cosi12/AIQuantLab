"""Strict, serializable contracts for market-behavior experiments."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aiquantlab.data.models import Timeframe


class ExpectedDirection(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    TWO_SIDED = "two_sided"


class ConditionOperator(StrEnum):
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "ge"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "le"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


class ConditionCombination(StrEnum):
    ALL = "all"
    ANY = "any"


class ReturnType(StrEnum):
    SIMPLE = "simple"
    LOG = "log"


class EventOverlapPolicy(StrEnum):
    ALLOW = "allow"
    NON_OVERLAPPING = "non_overlapping"


class BootstrapMethod(StrEnum):
    IID = "iid"
    MOVING_BLOCK = "moving_block"


class HypothesisDefinition(BaseModel):
    """A falsifiable market-behavior hypothesis, not a trading rule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(min_length=10)
    rationale: str = Field(min_length=10)
    null_hypothesis: str = Field(min_length=10)
    alternative_hypothesis: str = Field(min_length=10)
    expected_direction: ExpectedDirection = ExpectedDirection.TWO_SIDED
    falsification_criteria: tuple[str, ...] = Field(min_length=1)


class DatasetReference(BaseModel):
    """Immutable identity of the source file used by an experiment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    symbol: str = Field(min_length=1)
    timeframe: Timeframe

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class EventCondition(BaseModel):
    """One causal column comparison used to identify an event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left_column: str = Field(min_length=1)
    operator: ConditionOperator
    right_column: str | None = None
    value: int | float | bool | str | None = None
    left_lag_bars: int = Field(default=0, ge=0)
    right_lag_bars: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def require_one_comparison_target(self) -> Self:
        target_count = int(self.right_column is not None) + int(self.value is not None)
        if target_count != 1:
            raise ValueError("exactly one of right_column or value must be provided")
        if self.right_column is None and self.right_lag_bars:
            raise ValueError("right_lag_bars requires right_column")
        return self


class EventDefinition(BaseModel):
    """Interpretable conditions that define the event population."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=10)
    combination: ConditionCombination = ConditionCombination.ALL
    conditions: tuple[EventCondition, ...] = Field(min_length=1)


class EventStudySpecification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event: EventDefinition
    eligibility: EventDefinition | None = None
    price_column: str = "close"
    high_column: str = "high"
    low_column: str = "low"
    horizons_bars: tuple[int, ...] = Field(min_length=1)
    return_type: ReturnType = ReturnType.SIMPLE
    overlap_policy: EventOverlapPolicy = EventOverlapPolicy.ALLOW

    @field_validator("horizons_bars")
    @classmethod
    def horizons_must_be_positive_unique_and_sorted(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(horizon <= 0 for horizon in value):
            raise ValueError("all horizons_bars must be positive")
        if len(set(value)) != len(value):
            raise ValueError("horizons_bars must not contain duplicates")
        return tuple(sorted(value))


class StatisticalSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    confidence_level: float = Field(default=0.95, gt=0.5, lt=1.0)
    bootstrap_method: BootstrapMethod = BootstrapMethod.MOVING_BLOCK
    bootstrap_samples: int = Field(default=2_000, ge=100)
    block_size: int = Field(default=5, ge=1)
    random_seed: int = Field(default=7, ge=0)
    minimum_sample_size: int = Field(default=30, ge=2)


class ExperimentConfig(BaseModel):
    """Complete reproducible configuration for one experiment revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=1, ge=1)
    experiment_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,63}$")
    revision: int = Field(default=1, ge=1)
    title: str = Field(min_length=3)
    hypothesis: HypothesisDefinition
    dataset: DatasetReference
    event_study: EventStudySpecification
    statistics: StatisticalSpecification = Field(default_factory=StatisticalSpecification)
    tags: tuple[str, ...] = ()

    @field_validator("tags")
    @classmethod
    def tags_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("tags must be unique")
        return value

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class DistributionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    count: int = Field(ge=0)
    mean: float | None = None
    median: float | None = None
    standard_deviation: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    quantile_05: float | None = None
    quantile_25: float | None = None
    quantile_75: float | None = None
    quantile_95: float | None = None
    positive_probability: float | None = Field(default=None, ge=0.0, le=1.0)


class HorizonStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    horizon_bars: int = Field(gt=0)
    event_forward_return: DistributionSummary
    baseline_forward_return: DistributionSummary
    maximum_upside_return: DistributionSummary
    maximum_downside_return: DistributionSummary
    time_to_first_positive_bar: DistributionSummary
    time_to_first_negative_bar: DistributionSummary
    excess_mean_confidence_interval: tuple[float, float] | None = None
    excess_mean_return: float | None = None
    standardized_effect: float | None = None
    bootstrap_p_value: float | None = Field(default=None, ge=0.0, le=1.0)
    adjusted_q_value: float | None = Field(default=None, ge=0.0, le=1.0)
    warnings: tuple[str, ...] = ()


class StatisticalReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    experiment_id: str
    revision: int
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_direction: ExpectedDirection
    confidence_level: float
    bootstrap_method: BootstrapMethod
    bootstrap_samples: int
    random_seed: int
    multiple_testing_adjustment: str = "Benjamini-Hochberg"
    horizons: tuple[HorizonStatistics, ...]
    warnings: tuple[str, ...] = ()
