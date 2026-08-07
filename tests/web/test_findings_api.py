"""研究发现端点：被拒绝的发现必须保持可见与可追溯。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from synthetic_repository import CANDIDATE_ID, EXPERIMENT_ID, FINDING_ID


def test_rejected_finding_is_listed(client: TestClient) -> None:
    response = client.get("/api/findings")
    assert response.status_code == 200
    summaries = response.json()

    assert [summary["finding_id"] for summary in summaries] == [FINDING_ID]
    assert summaries[0]["status"] == "rejected"
    assert summaries[0]["source_experiment_id"] == EXPERIMENT_ID


def test_finding_summary_counts_limitations_and_non_claims(client: TestClient) -> None:
    summary = client.get("/api/findings").json()[0]

    assert summary["limitation_count"] == 1
    assert summary["non_claim_count"] == 1


def test_finding_detail_exposes_claim_boundaries(client: TestClient) -> None:
    payload = client.get(f"/api/findings/{FINDING_ID}").json()

    assert payload["market_behavior_claim"]
    assert payload["evidence_summary"]
    assert payload["economic_rationale"]
    assert payload["human_reviewer_notes"]
    # 局限与"明确不主张"是发现契约的一部分，界面不得省略。
    assert payload["limitations"]
    assert payload["explicit_non_claims"]


def test_finding_detail_carries_evidence_provenance(client: TestClient) -> None:
    evidence = client.get(f"/api/findings/{FINDING_ID}").json()["source_evidence"]

    assert evidence["experiment_id"] == EXPERIMENT_ID
    assert evidence["run_id"]
    assert evidence["statistical_report_sha256"]


def test_finding_detail_links_derived_candidates(client: TestClient) -> None:
    payload = client.get(f"/api/findings/{FINDING_ID}").json()
    assert payload["derived_candidate_ids"] == [CANDIDATE_ID]


def test_experiment_detail_links_related_findings(client: TestClient) -> None:
    payload = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()
    assert payload["related_finding_ids"] == [FINDING_ID]


def test_unknown_finding_returns_404(client: TestClient) -> None:
    assert client.get("/api/findings/FND-DOES-NOT-EXIST").status_code == 404
