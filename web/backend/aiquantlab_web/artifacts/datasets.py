"""从 data/processed 的 manifest sidecar 读取数据集身份、溯源与质量报告。

`data/processed` 下存在两类 manifest：

- OHLCV dataset manifest：含 `data_file`、`metadata`、`quality_report`。
- Feature dataset manifest：含 `output_file`、`feature_bundle`，没有独立 quality report，
  其溯源通过 `source_ohlcv_sha256` 指回 OHLCV 数据集。

两者都是研究者需要浏览的数据资产，因此都被建模，且 feature dataset 明确标注其
provenance 是继承而来，不伪装成独立采集的数据。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiquantlab_web.artifacts import coerce
from aiquantlab_web.artifacts.cache import FingerprintCache
from aiquantlab_web.artifacts.paths import (
    ensure_within,
    file_sha256,
    read_json,
    relative_to_repository,
    tree_fingerprint,
)
from aiquantlab_web.errors import ArtifactNotFoundError, ArtifactParseError
from aiquantlab_web.schemas import (
    DatasetDetail,
    DatasetIntegrity,
    DatasetPreview,
    DatasetProvenance,
    DatasetSummary,
    FeatureBundle,
    FeatureContract,
    QualityIssue,
    QualityReport,
    QualityReportEntry,
)
from aiquantlab_web.settings import ArtifactRoots

MANIFEST_SUFFIX = ".parquet.manifest.json"
KIND_OHLCV = "ohlcv"
KIND_FEATURE = "feature"

_PREVIEW_MAXIMUM_ROWS = 500
_cache: FingerprintCache[tuple[DatasetRecord, ...]] = FingerprintCache()


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    kind: str
    manifest_path: Path
    data_path: Path
    payload: dict[str, Any]


def _manifest_paths(roots: ArtifactRoots) -> list[Path]:
    if not roots.processed_data.is_dir():
        return []
    return sorted(roots.processed_data.glob(f"*{MANIFEST_SUFFIX}"))


def _classify(payload: dict[str, Any]) -> tuple[str, str | None]:
    """返回 (kind, data_file)。未知 schema 归为 OHLCV 并让字段留空。"""

    if coerce.as_str(payload, "output_file") or coerce.as_dict(payload, "feature_bundle"):
        return KIND_FEATURE, coerce.as_str(payload, "output_file")
    return KIND_OHLCV, coerce.as_str(payload, "data_file")


def load_records(roots: ArtifactRoots) -> tuple[DatasetRecord, ...]:
    paths = _manifest_paths(roots)
    fingerprint = tree_fingerprint(paths)

    def build() -> tuple[DatasetRecord, ...]:
        records: list[DatasetRecord] = []
        for path in paths:
            dataset_id = path.name.removesuffix(MANIFEST_SUFFIX)
            try:
                payload = read_json(path)
            except ArtifactParseError:
                continue
            kind, data_file = _classify(payload)
            records.append(
                DatasetRecord(
                    dataset_id=dataset_id,
                    kind=kind,
                    manifest_path=path,
                    data_path=path.parent / Path(data_file or f"{dataset_id}.parquet").name,
                    payload=payload,
                )
            )
        return tuple(records)

    return _cache.resolve(str(roots.processed_data), fingerprint, build)


def _find_record(roots: ArtifactRoots, dataset_id: str) -> DatasetRecord:
    for record in load_records(roots):
        if record.dataset_id == dataset_id:
            return record
    raise ArtifactNotFoundError(f"数据集不存在：{dataset_id}")


def _checksum(record: DatasetRecord) -> str | None:
    key = "output_sha256" if record.kind == KIND_FEATURE else "sha256"
    return coerce.as_str(record.payload, key)


def _build_quality_report(payload: dict[str, Any]) -> QualityReport:
    raw = coerce.as_dict(payload, "quality_report")
    issues = [
        QualityIssue(
            code=coerce.as_required_str(issue, "code", "unknown"),
            severity=coerce.as_required_str(issue, "severity", "unknown"),
            message=coerce.as_required_str(issue, "message", ""),
            count=coerce.as_int(issue, "count"),
            samples=[str(sample) for sample in coerce.as_list(issue, "samples")],
        )
        for issue in coerce.as_dict_list(raw, "issues")
    ]
    return QualityReport(
        passed=coerce.as_bool(raw, "passed"),
        row_count=coerce.as_int(raw, "row_count"),
        start=coerce.as_datetime(raw, "start"),
        end=coerce.as_datetime(raw, "end"),
        expected_candle_count=coerce.as_int(raw, "expected_candle_count"),
        missing_candle_count=coerce.as_int(raw, "missing_candle_count"),
        issues=issues,
        error_count=sum(1 for issue in issues if issue.severity == "error"),
        warning_count=sum(1 for issue in issues if issue.severity == "warning"),
        generated_at=coerce.as_datetime(raw, "generated_at"),
    )


def _build_provenance(payload: dict[str, Any]) -> DatasetProvenance:
    metadata = coerce.as_dict(payload, "metadata")
    return DatasetProvenance(
        symbol=coerce.as_str(metadata, "symbol"),
        source=coerce.as_str(metadata, "source"),
        timeframe=coerce.as_str(metadata, "timeframe"),
        source_timezone=coerce.as_str(metadata, "source_timezone"),
        canonical_timezone=coerce.as_str(metadata, "canonical_timezone"),
        timestamp_convention=coerce.as_str(metadata, "timestamp_convention"),
        price_basis=coerce.as_str(metadata, "price_basis"),
        volume_type=coerce.as_str(metadata, "volume_type"),
        calendar_policy=coerce.as_str(metadata, "calendar_policy"),
        notes=coerce.as_str_list(metadata, "notes"),
        created_at=coerce.as_datetime(metadata, "created_at"),
    )


def _columns(record: DatasetRecord) -> list[str]:
    if record.kind == KIND_FEATURE:
        return coerce.as_str_list(record.payload, "feature_columns")
    return coerce.as_str_list(record.payload, "columns")


def _source_record(
    record: DatasetRecord,
    records: tuple[DatasetRecord, ...],
) -> DatasetRecord | None:
    """通过 source_ohlcv_sha256 把 feature dataset 连回其 OHLCV 来源。"""

    if record.kind != KIND_FEATURE:
        return None
    source_checksum = coerce.as_str(record.payload, "source_ohlcv_sha256")
    source_file = coerce.as_str(record.payload, "source_ohlcv_file")
    for candidate in records:
        if candidate.kind != KIND_OHLCV:
            continue
        if source_checksum and _checksum(candidate) == source_checksum:
            return candidate
        if source_file and candidate.data_path.name == source_file:
            return candidate
    return None


def _summarize(record: DatasetRecord, records: tuple[DatasetRecord, ...]) -> DatasetSummary:
    payload = record.payload
    provenance = _build_provenance(payload)
    quality = _build_quality_report(payload)
    source = _source_record(record, records)
    inherited = False
    start = quality.start
    end = quality.end
    symbol = provenance.symbol
    timeframe = provenance.timeframe
    source_label = provenance.source

    if source is not None:
        source_provenance = _build_provenance(source.payload)
        source_quality = _build_quality_report(source.payload)
        symbol = symbol or source_provenance.symbol
        timeframe = timeframe or source_provenance.timeframe
        source_label = source_label or source_provenance.source
        start = start or source_quality.start
        end = end or source_quality.end
        inherited = True

    return DatasetSummary(
        dataset_id=record.dataset_id,
        kind=record.kind,
        data_file=record.data_path.name,
        symbol=symbol,
        timeframe=timeframe,
        source=source_label,
        start=start,
        end=end,
        row_count=coerce.as_int(payload, "row_count"),
        sha256=_checksum(record),
        column_count=len(_columns(record)),
        quality_passed=quality.passed,
        error_count=quality.error_count,
        warning_count=quality.warning_count,
        missing_candle_count=quality.missing_candle_count,
        data_file_exists=record.data_path.is_file(),
        created_at=coerce.as_datetime(payload, "created_at"),
        source_dataset_id=source.dataset_id if source is not None else None,
        provenance_inherited=inherited,
    )


def list_datasets(roots: ArtifactRoots) -> list[DatasetSummary]:
    records = load_records(roots)
    return [_summarize(record, records) for record in records]


def index_by_sha256(roots: ArtifactRoots) -> dict[str, str]:
    """dataset checksum → dataset_id，用于把实验反查回数据集。"""

    index: dict[str, str] = {}
    for record in load_records(roots):
        checksum = _checksum(record)
        if checksum:
            index[checksum] = record.dataset_id
    return index


def _build_feature_bundle(payload: dict[str, Any]) -> FeatureBundle | None:
    raw = coerce.as_dict(payload, "feature_bundle")
    if not raw:
        return None
    return FeatureBundle(
        bundle_id=coerce.as_str(raw, "bundle_id"),
        revision=coerce.as_int(raw, "revision"),
        features=[
            FeatureContract(
                name=coerce.as_str(feature, "name"),
                family=coerce.as_str(feature, "family"),
                input_columns=coerce.as_str_list(feature, "input_columns"),
                lookback_bars=coerce.as_int(feature, "lookback_bars"),
                uses_current_bar=coerce.as_bool(feature, "uses_current_bar"),
                warm_up_bars=coerce.as_int(feature, "warm_up_bars"),
                output_dtype=coerce.as_str(feature, "output_dtype"),
                economic_meaning=coerce.as_str(feature, "economic_meaning"),
                leakage_notes=coerce.as_str(feature, "leakage_notes"),
            )
            for feature in coerce.as_dict_list(raw, "features")
        ],
    )


def get_dataset(
    roots: ArtifactRoots,
    dataset_id: str,
    *,
    used_by_experiments: list[str] | None = None,
) -> DatasetDetail:
    records = load_records(roots)
    record = _find_record(roots, dataset_id)
    summary = _summarize(record, records)
    size_bytes = record.data_path.stat().st_size if record.data_path.is_file() else None
    derived = [
        candidate.dataset_id
        for candidate in records
        if (source := _source_record(candidate, records)) is not None
        and source.dataset_id == record.dataset_id
    ]
    return DatasetDetail(
        **summary.model_dump(),
        schema_version=coerce.as_int(record.payload, "schema_version"),
        columns=_columns(record) if record.kind == KIND_OHLCV else [],
        provenance=_build_provenance(record.payload),
        quality_report=_build_quality_report(record.payload),
        manifest_path=relative_to_repository(roots.repository, record.manifest_path),
        data_path=relative_to_repository(roots.repository, record.data_path),
        data_file_size_bytes=size_bytes,
        used_by_experiments=used_by_experiments or [],
        derived_dataset_ids=derived,
        feature_columns=coerce.as_str_list(record.payload, "feature_columns"),
        feature_bundle=_build_feature_bundle(record.payload),
        feature_bundle_sha256=coerce.as_str(record.payload, "feature_bundle_sha256"),
        source_ohlcv_sha256=coerce.as_str(record.payload, "source_ohlcv_sha256"),
        validity_column=coerce.as_str(record.payload, "validity_column"),
        warm_up_bars=coerce.as_int(record.payload, "warm_up_bars"),
        code_version=coerce.as_str(record.payload, "code_version"),
    )


def quality_reports(roots: ArtifactRoots) -> list[QualityReportEntry]:
    records = load_records(roots)
    entries: list[QualityReportEntry] = []
    for record in records:
        summary = _summarize(record, records)
        entries.append(
            QualityReportEntry(
                dataset_id=record.dataset_id,
                kind=record.kind,
                symbol=summary.symbol,
                timeframe=summary.timeframe,
                row_count=summary.row_count,
                quality_report=_build_quality_report(record.payload),
            )
        )
    return entries


def verify_integrity(roots: ArtifactRoots, dataset_id: str) -> DatasetIntegrity:
    """对 parquet 文件计算完整 SHA-256。这是有意的慢操作，必须由用户显式触发。"""

    record = _find_record(roots, dataset_id)
    data_path = ensure_within(roots.readable_roots, record.data_path)
    expected = _checksum(record)
    if not data_path.is_file():
        return DatasetIntegrity(
            dataset_id=dataset_id,
            expected_sha256=expected,
            actual_sha256=None,
            matches=False,
            data_file_size_bytes=None,
            checked_at=datetime.now(UTC),
        )
    actual = file_sha256(data_path)
    return DatasetIntegrity(
        dataset_id=dataset_id,
        expected_sha256=expected,
        actual_sha256=actual,
        matches=bool(expected) and actual == expected,
        data_file_size_bytes=data_path.stat().st_size,
        checked_at=datetime.now(UTC),
    )


def preview(
    roots: ArtifactRoots,
    dataset_id: str,
    *,
    position: str = "head",
    limit: int = 20,
) -> DatasetPreview:
    record = _find_record(roots, dataset_id)
    data_path = ensure_within(roots.readable_roots, record.data_path)
    if not data_path.is_file():
        raise ArtifactNotFoundError(f"数据文件不存在：{record.data_path.name}")

    bounded_limit = max(1, min(limit, _PREVIEW_MAXIMUM_ROWS))
    import pandas as pd  # 延迟导入：仅预览端点需要 pandas。

    frame = pd.read_parquet(data_path, engine="pyarrow")
    selected = frame.tail(bounded_limit) if position == "tail" else frame.head(bounded_limit)
    # 借用 pandas 的 JSON 序列化统一处理时区、NaN 与 nullable dtype。
    rows = json.loads(selected.to_json(orient="records", date_format="iso"))
    return DatasetPreview(
        dataset_id=dataset_id,
        position="tail" if position == "tail" else "head",
        limit=bounded_limit,
        row_count=len(rows),
        columns=[str(column) for column in frame.columns],
        rows=rows,
    )
