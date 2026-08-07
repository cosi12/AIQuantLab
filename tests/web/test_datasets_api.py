"""数据集端点：身份、溯源、质量与完整性。"""

from __future__ import annotations

from aiquantlab_web.settings import ArtifactRoots
from fastapi.testclient import TestClient
from synthetic_repository import FEATURE_DATASET_ID, OHLCV_DATASET_ID


def test_dataset_list_models_both_manifest_kinds(client: TestClient) -> None:
    response = client.get("/api/datasets")
    assert response.status_code == 200
    by_id = {item["dataset_id"]: item for item in response.json()}

    ohlcv = by_id[OHLCV_DATASET_ID]
    assert ohlcv["kind"] == "ohlcv"
    assert ohlcv["symbol"] == "XAUUSD"
    assert ohlcv["timeframe"] == "M15"
    assert ohlcv["provenance_inherited"] is False
    assert ohlcv["source_dataset_id"] is None

    feature = by_id[FEATURE_DATASET_ID]
    assert feature["kind"] == "feature"
    # feature manifest 自身没有 symbol/timeframe，必须显式标注是继承来的。
    assert feature["symbol"] == "XAUUSD"
    assert feature["provenance_inherited"] is True
    assert feature["source_dataset_id"] == OHLCV_DATASET_ID


def test_dataset_list_reports_warnings_without_flipping_passed(client: TestClient) -> None:
    datasets = client.get("/api/datasets").json()
    ohlcv = next(item for item in datasets if item["dataset_id"] == OHLCV_DATASET_ID)
    # 通过校验但存在警告：两者必须同时可见，不能用 passed 掩盖警告。
    assert ohlcv["quality_passed"] is True
    assert ohlcv["warning_count"] == 1
    assert ohlcv["error_count"] == 0
    assert ohlcv["missing_candle_count"] == 2


def test_dataset_detail_exposes_provenance_and_quality(client: TestClient) -> None:
    response = client.get(f"/api/datasets/{OHLCV_DATASET_ID}")
    assert response.status_code == 200
    payload = response.json()

    provenance = payload["provenance"]
    assert provenance["timestamp_convention"] == "bar_open"
    assert provenance["price_basis"] == "bid"
    assert provenance["volume_type"] == "tick_activity"
    assert provenance["notes"]

    issue = payload["quality_report"]["issues"][0]
    assert issue["code"] == "missing_candles"
    assert issue["severity"] == "warning"
    assert issue["samples"]

    assert payload["columns"] == ["timestamp", "open", "high", "low", "close", "volume"]
    assert payload["manifest_path"].startswith("data/processed/")
    assert payload["data_file_exists"] is True
    assert payload["derived_dataset_ids"] == [FEATURE_DATASET_ID]


def test_feature_dataset_detail_exposes_bundle_and_leakage_notes(client: TestClient) -> None:
    payload = client.get(f"/api/datasets/{FEATURE_DATASET_ID}").json()

    assert payload["feature_columns"] == ["body_fraction"]
    assert payload["validity_column"] == "feature_valid"
    assert payload["warm_up_bars"] == 3
    bundle = payload["feature_bundle"]
    assert bundle["bundle_id"] == "SYN-BUNDLE-001"
    feature = bundle["features"][0]
    assert feature["uses_current_bar"] is True
    assert feature["leakage_notes"]


def test_dataset_detail_links_back_to_experiments(client: TestClient) -> None:
    payload = client.get(f"/api/datasets/{FEATURE_DATASET_ID}").json()
    assert payload["used_by_experiments"] == ["SYN-XAUUSD-M15-001"]


def test_dataset_integrity_recomputes_checksum(client: TestClient) -> None:
    response = client.get(f"/api/datasets/{OHLCV_DATASET_ID}/integrity")
    assert response.status_code == 200
    payload = response.json()

    assert payload["matches"] is True
    assert payload["actual_sha256"] == payload["expected_sha256"]
    assert payload["data_file_size_bytes"] > 0


def test_dataset_integrity_detects_mutated_file(client: TestClient, roots: ArtifactRoots) -> None:
    data_path = roots.processed_data / f"{OHLCV_DATASET_ID}.parquet"
    data_path.write_bytes(data_path.read_bytes() + b"tampered")

    payload = client.get(f"/api/datasets/{OHLCV_DATASET_ID}/integrity").json()
    assert payload["matches"] is False
    assert payload["actual_sha256"] != payload["expected_sha256"]


def test_dataset_preview_respects_position_and_limit(client: TestClient) -> None:
    head = client.get(f"/api/datasets/{OHLCV_DATASET_ID}/preview", params={"limit": 3}).json()
    tail = client.get(
        f"/api/datasets/{OHLCV_DATASET_ID}/preview",
        params={"limit": 3, "position": "tail"},
    ).json()

    assert head["position"] == "head"
    assert head["row_count"] == 3
    assert tail["position"] == "tail"
    assert head["rows"][0]["open"] != tail["rows"][0]["open"]


def test_dataset_preview_rejects_out_of_range_limit(client: TestClient) -> None:
    assert (
        client.get(f"/api/datasets/{OHLCV_DATASET_ID}/preview", params={"limit": 0}).status_code
        == 422
    )
    assert (
        client.get(f"/api/datasets/{OHLCV_DATASET_ID}/preview", params={"limit": 5000}).status_code
        == 422
    )


def test_unknown_dataset_returns_404(client: TestClient) -> None:
    assert client.get("/api/datasets/does_not_exist").status_code == 404


def test_quality_reports_cover_every_dataset(client: TestClient) -> None:
    entries = client.get("/api/quality-reports").json()
    assert {entry["dataset_id"] for entry in entries} == {OHLCV_DATASET_ID, FEATURE_DATASET_ID}
