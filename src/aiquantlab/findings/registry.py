"""Single-process immutable finding publication with promotion gates."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from aiquantlab.data.storage import file_sha256
from aiquantlab.findings.models import (
    FindingStatus,
    ResearchFinding,
    SourceExperimentEvidence,
)
from aiquantlab.research.models import EventDefinition, ExperimentConfig
from aiquantlab.research.registry import (
    ExperimentConclusion,
    ExperimentRegistry,
    RunStatus,
)


class FindingRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    findings: tuple[ResearchFinding, ...] = ()


class FindingRegistry:
    """A compact index plus one immutable JSON artifact per finding."""

    def __init__(self, index_path: str | Path, artifact_root: str | Path) -> None:
        self.index_path = Path(index_path)
        self.artifact_root = Path(artifact_root)

    def _load(self) -> FindingRegistryDocument:
        if not self.index_path.exists():
            return FindingRegistryDocument()
        return FindingRegistryDocument.model_validate_json(
            self.index_path.read_text(encoding="utf-8")
        )

    def list_findings(self) -> tuple[ResearchFinding, ...]:
        return self._load().findings

    def publish(self, finding: ResearchFinding) -> Path:
        document = self._load()
        if any(existing.finding_id == finding.finding_id for existing in document.findings):
            raise ValueError(f"finding already exists: {finding.finding_id}")
        artifact_path = self.artifact_root / finding.finding_id / "finding.json"
        if artifact_path.exists():
            raise FileExistsError(artifact_path)

        artifact_path.parent.mkdir(parents=True, exist_ok=False)
        artifact_path.write_text(finding.model_dump_json(indent=2), encoding="utf-8")
        updated = document.model_copy(update={"findings": (*document.findings, finding)})
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.index_path.with_name(f".{self.index_path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.index_path)
        except Exception:
            artifact_path.unlink(missing_ok=True)
            artifact_path.parent.rmdir()
            raise
        finally:
            temporary.unlink(missing_ok=True)
        return artifact_path


def promote_finding(
    *,
    registry: ExperimentRegistry,
    finding_registry: FindingRegistry,
    config: ExperimentConfig,
    run_id: str,
    statistical_report_path: str | Path,
    finding_id: str,
    title: str,
    status: FindingStatus,
    market_behavior_claim: str,
    applicable_event: EventDefinition,
    evidence_summary: str,
    limitations: tuple[str, ...],
    economic_rationale: str,
    explicit_non_claims: tuple[str, ...],
    human_reviewer_notes: str,
) -> ResearchFinding:
    """Publish only completed, manually reviewed experiment evidence."""

    registered = registry.get_experiment(config.experiment_id, config.revision)
    if registered.config_sha256 != config.fingerprint():
        raise ValueError("registered experiment configuration does not match promotion input")
    if registered.conclusion == ExperimentConclusion.NOT_REVIEWED:
        raise ValueError("experiment requires a human-reviewed conclusion before promotion")
    accepted_without_support = (
        status == FindingStatus.ACCEPTED_FOR_RESEARCH
        and registered.conclusion != ExperimentConclusion.SUPPORTED
    )
    if accepted_without_support:
        raise ValueError("accepted findings require a supported experiment conclusion")
    source_run = next((run for run in registered.runs if run.run_id == run_id), None)
    if source_run is None or source_run.status != RunStatus.COMPLETED:
        raise ValueError("finding evidence must reference a completed run")
    report_path = Path(statistical_report_path)
    if not report_path.is_file():
        raise FileNotFoundError(report_path)

    finding = ResearchFinding(
        finding_id=finding_id,
        title=title,
        status=status,
        source_evidence=SourceExperimentEvidence(
            experiment_id=config.experiment_id,
            revision=config.revision,
            run_id=run_id,
            config_sha256=config.fingerprint(),
            dataset_sha256=config.dataset.sha256,
            statistical_report_sha256=file_sha256(report_path),
            conclusion=registered.conclusion,
        ),
        symbol=config.dataset.symbol,
        timeframe=config.dataset.timeframe,
        market_behavior_claim=market_behavior_claim,
        applicable_event=applicable_event,
        evidence_summary=evidence_summary,
        limitations=limitations,
        economic_rationale=economic_rationale,
        explicit_non_claims=explicit_non_claims,
        human_reviewer_notes=human_reviewer_notes,
        reviewed_at=datetime.now(UTC),
    )
    finding_registry.publish(finding)
    return finding
