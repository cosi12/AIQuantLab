"""Contracts separating reviewed market evidence from executable strategies."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aiquantlab.data.models import Timeframe
from aiquantlab.research.models import EventDefinition
from aiquantlab.research.registry import ExperimentConclusion


class FindingStatus(StrEnum):
    ACCEPTED_FOR_RESEARCH = "accepted_for_research"
    REJECTED = "rejected"


class SourceExperimentEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str
    revision: int = Field(ge=1)
    run_id: str
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    statistical_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    conclusion: ExperimentConclusion


class ResearchFinding(BaseModel):
    """A reviewed market-behavior claim with explicit limitations and non-claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    finding_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._-]{2,63}$")
    title: str = Field(min_length=3)
    status: FindingStatus
    source_evidence: SourceExperimentEvidence
    symbol: str = Field(min_length=1)
    timeframe: Timeframe
    market_behavior_claim: str = Field(min_length=20)
    applicable_event: EventDefinition
    evidence_summary: str = Field(min_length=20)
    limitations: tuple[str, ...] = Field(min_length=1)
    economic_rationale: str = Field(min_length=20)
    explicit_non_claims: tuple[str, ...] = Field(min_length=1)
    human_reviewer_notes: str = Field(min_length=20)
    reviewed_at: datetime

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("limitations", "explicit_non_claims")
    @classmethod
    def entries_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("finding list entries must be unique")
        return value

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
