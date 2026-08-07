"""总览、健康检查、报告查看器与空仓库行为。"""

from __future__ import annotations

from aiquantlab_web.settings import ArtifactRoots
from fastapi.testclient import TestClient
from synthetic_repository import CANDIDATE_ID, EXPERIMENT_ID, FINDING_ID, REPORT_NAME


def test_health_reports_artifact_roots(client: TestClient, roots: ArtifactRoots) -> None:
    payload = client.get("/api/health").json()

    assert payload["status"] == "ok"
    assert payload["repository_root"] == str(roots.repository)
    assert payload["roots"]["processed_data"]["exists"] is True


def test_overview_counts_match_artifacts(client: TestClient) -> None:
    payload = client.get("/api/overview").json()
    counts = payload["counts"]

    assert counts["datasets"] == 2
    assert counts["experiments"] == 1
    assert counts["experiment_runs"] == 2
    assert counts["findings"] == 1
    assert counts["strategy_candidates"] == 1
    assert counts["reports"] == 1


def test_overview_tallies_use_raw_artifact_status(client: TestClient) -> None:
    payload = client.get("/api/overview").json()

    assert payload["experiments_by_conclusion"] == [{"label": "not_supported", "count": 1}]
    assert payload["findings_by_status"] == [{"label": "rejected", "count": 1}]
    assert payload["candidates_by_display_status"] == [{"label": "PIPELINE_PROBE", "count": 1}]


def test_overview_latest_results_cover_every_artifact_kind(client: TestClient) -> None:
    results = client.get("/api/overview").json()["latest_results"]
    by_kind = {result["kind"]: result for result in results}

    assert by_kind["experiment"]["identifier"] == EXPERIMENT_ID
    assert by_kind["experiment"]["status"] == "not_supported"
    assert by_kind["finding"]["identifier"] == FINDING_ID
    assert by_kind["candidate"]["identifier"] == CANDIDATE_ID
    assert by_kind["candidate"]["status"] == "PIPELINE_PROBE"


def test_overview_surfaces_dataset_warnings_and_notices(client: TestClient) -> None:
    payload = client.get("/api/overview").json()

    assert payload["dataset_warning_total"] == 1
    assert len(payload["notices"]) == 3
    checks = {check["name"]: check for check in payload["system_checks"]}
    assert checks["write_access"]["ok"] is True
    assert checks["processed_data"]["ok"] is True


def test_report_listing_and_content(client: TestClient) -> None:
    summaries = client.get("/api/reports").json()
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["file_name"] == REPORT_NAME
    assert summary["title"] == "合成研究记录"

    payload = client.get(f"/api/reports/{summary['report_id']}").json()
    assert payload["content"].startswith("# 合成研究记录")


def test_unknown_report_returns_404(client: TestClient) -> None:
    assert client.get("/api/reports/absent").status_code == 404


def test_api_exposes_no_write_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    methods = {method for operations in paths.values() for method in operations}

    assert methods == {"get"}


def test_empty_repository_returns_empty_collections(empty_client: TestClient) -> None:
    for endpoint in ("/api/datasets", "/api/experiments", "/api/findings", "/api/candidates"):
        response = empty_client.get(endpoint)
        assert response.status_code == 200
        assert response.json() == []


def test_empty_repository_overview_reports_missing_roots(empty_client: TestClient) -> None:
    payload = empty_client.get("/api/overview").json()

    assert payload["counts"]["datasets"] == 0
    assert payload["latest_results"] == []
    checks = {check["name"]: check["ok"] for check in payload["system_checks"]}
    # 目录缺失必须被明确报告为不可用，而不是静默呈现为正常。
    assert checks["processed_data"] is False
    assert checks["experiments"] is False
    assert checks["write_access"] is True
