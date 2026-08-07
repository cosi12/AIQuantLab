"""实验端点：假设、配置、统计证据与研究诚实性。"""

from __future__ import annotations

import pytest
from aiquantlab_web.artifacts import experiments as experiment_artifacts
from aiquantlab_web.errors import ArtifactPathError
from aiquantlab_web.settings import ArtifactRoots
from fastapi.testclient import TestClient
from synthetic_repository import (
    EXPERIMENT_ID,
    FAILED_RUN_ID,
    FEATURE_DATASET_ID,
    RUN_ID,
)


def test_experiment_list_preserves_negative_conclusion(client: TestClient) -> None:
    response = client.get("/api/experiments")
    assert response.status_code == 200
    summary = response.json()[0]

    assert summary["experiment_id"] == EXPERIMENT_ID
    assert summary["conclusion"] == "not_supported"
    assert summary["conclusion_notes"]
    assert summary["hypothesis_statement"]
    assert summary["registered_at"] is not None


def test_experiment_list_reports_failed_runs(client: TestClient) -> None:
    summary = client.get("/api/experiments").json()[0]

    # 失败运行必须计入并可见，否则界面会把不完整证据呈现为完整证据。
    assert summary["run_count"] == 2
    assert summary["completed_run_count"] == 1
    assert summary["failed_run_count"] == 1
    assert summary["latest_run_status"] == "completed"


def test_experiment_summary_derives_event_and_horizons_from_config(client: TestClient) -> None:
    summary = client.get("/api/experiments").json()[0]

    assert summary["event_name"] == "synthetic_bullish"
    assert summary["horizons_bars"] == [4, 8]
    assert summary["symbol"] == "XAUUSD"
    assert summary["timeframe"] == "M15"
    assert summary["registry_name"] == "synthetic_lab"


def test_experiment_detail_exposes_hypothesis_and_falsification(client: TestClient) -> None:
    payload = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()

    hypothesis = payload["hypothesis"]
    assert hypothesis["null_hypothesis"]
    assert hypothesis["alternative_hypothesis"]
    assert hypothesis["expected_direction"] == "positive"
    assert hypothesis["falsification_criteria"]


def test_experiment_detail_links_dataset_by_checksum(client: TestClient) -> None:
    payload = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()

    assert payload["dataset"]["dataset_id"] == FEATURE_DATASET_ID
    assert payload["feature_dataset"]["validity_column"] == "feature_valid"


def test_experiment_detail_exposes_event_definition_with_lag(client: TestClient) -> None:
    event = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()["event_study"]["event"]

    condition = event["conditions"][0]
    assert condition["left_column"] == "close"
    assert condition["operator"] == "greater_than"
    assert condition["left_lag_bars"] == 0


def test_statistical_evidence_marks_interval_containing_zero(client: TestClient) -> None:
    report = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()["statistical_report"]

    assert report["significance_threshold"] == 0.05
    assert report["multiple_testing_adjustment"] == "benjamini_hochberg"
    for horizon in report["horizons"]:
        # 两个 horizon 的区间都跨零、q 值都高于阈值：不得被呈现为显著。
        assert horizon["confidence_interval_includes_zero"] is True
        assert horizon["passes_significance_threshold"] is False


def test_statistical_report_keeps_warnings(client: TestClient) -> None:
    report = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()["statistical_report"]

    assert report["warnings"]
    assert report["horizons"][1]["warnings"]


def test_experiment_detail_resolves_run_directory_despite_stale_absolute_path(
    client: TestClient,
) -> None:
    payload = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()

    # registry 记录的绝对路径不存在，仍应通过约定目录结构定位到 run。
    assert payload["evidence_run_id"] == RUN_ID
    assert payload["run_integrity"]["selected_event_count"] == 40
    completed = next(run for run in payload["runs"] if run["run_id"] == RUN_ID)
    assert completed["artifacts_available"] is True
    assert completed["artifact_directory"].startswith("experiments/synthetic_lab/")


def test_failed_run_is_listed_with_its_error(client: TestClient) -> None:
    runs = client.get(f"/api/experiments/{EXPERIMENT_ID}").json()["runs"]
    failed = next(run for run in runs if run["run_id"] == FAILED_RUN_ID)

    assert failed["status"] == "failed"
    assert failed["error"]
    assert failed["artifacts_available"] is False


def test_experiment_detail_accepts_explicit_run_id(client: TestClient) -> None:
    payload = client.get(
        f"/api/experiments/{EXPERIMENT_ID}", params={"run_id": FAILED_RUN_ID}
    ).json()

    assert payload["evidence_run_id"] == FAILED_RUN_ID
    # 失败运行没有 artifact，因此不得凭空生成统计报告。
    assert payload["statistical_report"] is None


def test_experiment_detail_rejects_unknown_run_and_revision(client: TestClient) -> None:
    assert (
        client.get(f"/api/experiments/{EXPERIMENT_ID}", params={"run_id": "0" * 32}).status_code
        == 404
    )
    assert (
        client.get(f"/api/experiments/{EXPERIMENT_ID}", params={"revision": 9}).status_code == 404
    )
    assert client.get("/api/experiments/NO-SUCH-EXPERIMENT").status_code == 404


def test_run_artifact_listing_reports_recorded_checksums(client: TestClient) -> None:
    files = client.get(f"/api/experiments/{EXPERIMENT_ID}/runs/{RUN_ID}/artifacts").json()
    by_name = {item["name"]: item for item in files}

    assert by_name["config.resolved.json"]["recorded_sha256"] == "1" * 64
    assert by_name["run_manifest.json"]["recorded_sha256"] is None
    assert by_name["statistical_report.json"]["is_json"] is True
    assert all(item["size_bytes"] > 0 for item in files)


def test_run_artifact_content_is_returned_verbatim(client: TestClient) -> None:
    response = client.get(
        f"/api/experiments/{EXPERIMENT_ID}/runs/{RUN_ID}/artifacts/statistical_report.json"
    )
    assert response.status_code == 200
    assert response.json()["experiment_id"] == EXPERIMENT_ID


def test_run_artifact_rejects_non_json_and_missing_names(client: TestClient) -> None:
    base = f"/api/experiments/{EXPERIMENT_ID}/runs/{RUN_ID}/artifacts"

    # 表格类 artifact 不走 JSON 端点；缺失的名字必须是 404 而不是空对象。
    assert client.get(f"{base}/report.parquet").status_code == 422
    assert client.get(f"{base}/absent.json").status_code == 404


def test_run_artifact_traversal_never_returns_content(client: TestClient) -> None:
    base = f"/api/experiments/{EXPERIMENT_ID}/runs/{RUN_ID}/artifacts"

    for name in ("..%2F..%2Fexperiment_registry.json", "%2E%2E%2Fconfig.resolved.json"):
        response = client.get(f"{base}/{name}")
        assert response.status_code in {400, 404}


@pytest.mark.parametrize("artifact_name", ["../config.resolved.json", "nested/config.json"])
def test_read_run_artifact_rejects_path_semantics(
    roots: ArtifactRoots,
    artifact_name: str,
) -> None:
    """HTTP 路由会先归一化路径，因此越权防护必须在 artifact 层独立成立。"""

    with pytest.raises(ArtifactPathError):
        experiment_artifacts.read_run_artifact(roots, EXPERIMENT_ID, RUN_ID, artifact_name)
