from __future__ import annotations

import pytest

from aiquantlab.findings import FindingRegistry, FindingStatus, promote_finding
from aiquantlab.research import ExperimentConclusion, ExperimentRegistry


def test_promotion_requires_supported_reviewed_completed_evidence(
    experiment_config,
    tmp_path,
) -> None:
    experiment_registry = ExperimentRegistry(tmp_path / "experiments.json")
    experiment_registry.register(experiment_config)
    run = experiment_registry.begin_run(experiment_config, code_version="test")
    experiment_registry.complete_run(
        run.run_id,
        frame_sha256="f" * 64,
        artifact_directory=str(tmp_path / "run"),
    )
    report_path = tmp_path / "statistical_report.json"
    report_path.write_text("{}", encoding="utf-8")
    finding_registry = FindingRegistry(
        tmp_path / "findings" / "index.json",
        tmp_path / "findings",
    )

    with pytest.raises(ValueError, match="human-reviewed"):
        promote_finding(
            registry=experiment_registry,
            finding_registry=finding_registry,
            config=experiment_config,
            run_id=run.run_id,
            statistical_report_path=report_path,
            finding_id="FND-TEST-001",
            title="Test finding",
            status=FindingStatus.ACCEPTED_FOR_RESEARCH,
            market_behavior_claim="A sufficiently long test market behavior claim.",
            applicable_event=experiment_config.event_study.event,
            evidence_summary="A sufficiently long evidence summary for testing.",
            limitations=("Synthetic evidence only.",),
            economic_rationale="A sufficiently long economic rationale for testing.",
            explicit_non_claims=("This is not a trading rule.",),
            human_reviewer_notes="A sufficiently detailed human review note for testing.",
        )

    experiment_registry.set_conclusion(
        experiment_config.experiment_id,
        experiment_config.revision,
        conclusion=ExperimentConclusion.SUPPORTED,
        notes="Synthetic promotion-gate test with no market claim.",
    )
    finding = promote_finding(
        registry=experiment_registry,
        finding_registry=finding_registry,
        config=experiment_config,
        run_id=run.run_id,
        statistical_report_path=report_path,
        finding_id="FND-TEST-001",
        title="Test finding",
        status=FindingStatus.ACCEPTED_FOR_RESEARCH,
        market_behavior_claim="A sufficiently long test market behavior claim.",
        applicable_event=experiment_config.event_study.event,
        evidence_summary="A sufficiently long evidence summary for testing.",
        limitations=("Synthetic evidence only.",),
        economic_rationale="A sufficiently long economic rationale for testing.",
        explicit_non_claims=("This is not a trading rule.",),
        human_reviewer_notes="A sufficiently detailed human review note for testing.",
    )

    assert finding_registry.list_findings() == (finding,)
    assert (tmp_path / "findings" / finding.finding_id / "finding.json").is_file()
