"""策略候选端点与展示状态派生规则。

展示状态是 Web 层唯一的派生语义，因此它的优先级必须被逐条钉住，避免未来把
pipeline probe 或来源被拒的候选渲染成"通过验证"。
"""

from __future__ import annotations

import pytest
from aiquantlab_web.artifacts.candidates import (
    DISPLAY_NOT_SUPPORTED,
    DISPLAY_PENDING_REVIEW,
    DISPLAY_PIPELINE_PROBE,
    DISPLAY_REJECTED,
    DISPLAY_SUPPORTED,
    derive_display_status,
)
from fastapi.testclient import TestClient
from synthetic_repository import CANDIDATE_ID, FINDING_ID


@pytest.mark.parametrize(
    ("purpose", "finding_status", "assessment", "has_report", "expected"),
    [
        # pipeline probe 优先级最高：即使验证结论是 supported 也不得渲染为 supported。
        ("pipeline_probe", "accepted_for_research", "supported", True, DISPLAY_PIPELINE_PROBE),
        ("pipeline_probe", "rejected", "not_supported", True, DISPLAY_PIPELINE_PROBE),
        # 来源发现被拒绝时，候选状态由来源决定，而不是由验证指标决定。
        ("strategy_candidate", "rejected", "supported", True, DISPLAY_REJECTED),
        # 没有验证报告一律待审，不得默认乐观或默认否定。
        ("strategy_candidate", "accepted_for_research", None, False, DISPLAY_PENDING_REVIEW),
        ("strategy_candidate", "accepted_for_research", "supported", True, DISPLAY_SUPPORTED),
        ("strategy_candidate", "accepted_for_research", "not_supported", True,
         DISPLAY_NOT_SUPPORTED),
        # 未知 assessment 退回待审，而不是猜测成通过。
        ("strategy_candidate", "accepted_for_research", "weird_value", True,
         DISPLAY_PENDING_REVIEW),
        (None, None, None, False, DISPLAY_PENDING_REVIEW),
    ],
)
def test_display_status_priority(
    purpose: str | None,
    finding_status: str | None,
    assessment: str | None,
    has_report: bool,
    expected: str,
) -> None:
    assert (
        derive_display_status(
            purpose=purpose,
            source_finding_status=finding_status,
            assessment=assessment,
            has_validation_report=has_report,
        )
        == expected
    )


def test_candidate_list_marks_pipeline_probe(client: TestClient) -> None:
    response = client.get("/api/candidates")
    assert response.status_code == 200
    summary = response.json()[0]

    assert summary["candidate_id"] == CANDIDATE_ID
    assert summary["purpose"] == "pipeline_probe"
    assert summary["research_gate_passed"] is False
    assert summary["display_status"] == DISPLAY_PIPELINE_PROBE
    assert summary["validation_assessment"] == "not_supported"
    assert summary["validated"] is True
    assert summary["validated_at"] is not None


def test_candidate_list_carries_source_finding_status(client: TestClient) -> None:
    summary = client.get("/api/candidates").json()[0]

    assert summary["source_finding_id"] == FINDING_ID
    assert summary["source_finding_status"] == "rejected"


def test_candidate_detail_exposes_frozen_rules(client: TestClient) -> None:
    payload = client.get(f"/api/candidates/{CANDIDATE_ID}").json()

    assert payload["signal_semantics"]
    assert payload["execution_timing"] == "next_bar_open"
    assert payload["assumptions"]
    assert payload["entry_event"]["conditions"][0]["left_column"] == "close"
    assert payload["position_sizing"]["method"] == "fixed_fraction"
    assert payload["risk_rules"]["maximum_concurrent_positions"] == 1


def test_candidate_detail_exposes_validation_plan_criteria(client: TestClient) -> None:
    plan = client.get(f"/api/candidates/{CANDIDATE_ID}").json()["validation_plan"]

    assert plan["frozen_before_validation"] is True
    assert plan["research_gate_passed"] is False
    assert plan["criteria"]["minimum_trades_per_evaluation_split"] == 30
    assert [split["role"] for split in plan["splits"]] == ["development", "holdout"]


def test_candidate_detail_exposes_split_failures_and_stress(client: TestClient) -> None:
    report = client.get(f"/api/candidates/{CANDIDATE_ID}").json()["validation_report"]

    assert report["assessment"] == "not_supported"
    assert report["warnings"]
    result = report["split_results"][0]
    assert result["criteria_passed"] is False
    # 失败原因必须逐条保留，而不是折叠成一个布尔值。
    assert result["failures"] == ["insufficient_trades", "non_positive_mean_return"]
    # 压力情景必须与主情景并列展示，避免只看乐观执行假设。
    assert result["stress"]["cumulative_return"] < result["primary"]["cumulative_return"]


def test_candidate_detail_reports_artifact_locations(client: TestClient) -> None:
    payload = client.get(f"/api/candidates/{CANDIDATE_ID}").json()

    assert payload["artifact_path"].endswith("strategy_candidate.json")
    assert payload["validation_manifest"] == {"code_version": "test"}
    assert payload["trade_ledgers"] == []


def test_unknown_candidate_returns_404(client: TestClient) -> None:
    assert client.get("/api/candidates/CAND-DOES-NOT-EXIST").status_code == 404
