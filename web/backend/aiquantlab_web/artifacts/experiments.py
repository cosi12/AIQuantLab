"""从 experiment registry 与不可变 run 目录读取实验、配置与统计证据。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiquantlab.research.registry import ExperimentConclusion, RunStatus
from aiquantlab_web.artifacts import coerce, datasets
from aiquantlab_web.artifacts.cache import FingerprintCache
from aiquantlab_web.artifacts.paths import (
    ensure_plain_name,
    ensure_within,
    read_json,
    relative_to_repository,
    tree_fingerprint,
)
from aiquantlab_web.errors import ArtifactNotFoundError, ArtifactParseError
from aiquantlab_web.schemas import (
    ArtifactFile,
    DatasetReferenceView,
    DistributionSummary,
    EventCondition,
    EventDefinition,
    EventStudyView,
    ExperimentDetail,
    ExperimentSummary,
    FeatureDatasetView,
    HorizonStatistics,
    HypothesisView,
    RunIntegrity,
    RunSummary,
    StatisticalReport,
    StatisticalSpecificationView,
)
from aiquantlab_web.settings import ArtifactRoots

CONFIG_ARTIFACT = "config.resolved.json"
STATISTICAL_REPORT_ARTIFACT = "statistical_report.json"
RUN_MANIFEST_ARTIFACT = "run_manifest.json"

# 预声明的多重检验阈值。UI 不得使用其他阈值重新解释 q-value。
SIGNIFICANCE_THRESHOLD = 0.05

_index_cache: FingerprintCache[tuple[ExperimentRecord, ...]] = FingerprintCache()


@dataclass(frozen=True)
class ExperimentRecord:
    experiment_id: str
    revision: int
    registry_path: Path
    registry_name: str
    entry: dict[str, Any]
    run_directories: dict[str, Path]


def _registry_paths(roots: ArtifactRoots) -> list[Path]:
    if not roots.experiments.is_dir():
        return []
    return sorted(path for path in roots.experiments.rglob("*registry*.json") if path.is_file())


def _registry_name(roots: ArtifactRoots, path: Path) -> str:
    if path.parent.resolve() == roots.experiments.resolve():
        return path.stem.removesuffix("_registry").removeprefix("experiment_") or path.stem
    return path.parent.name


def _run_directory_index(roots: ArtifactRoots) -> dict[str, Path]:
    """run_id → run 目录。

    registry 记录的 artifact_directory 是生成时的绝对路径，跨机器不可移植，
    因此优先按约定结构 `<...>/revision-<n>/<run_id>/` 定位。
    """

    index: dict[str, Path] = {}
    if not roots.experiments.is_dir():
        return index
    for revision_directory in roots.experiments.rglob("revision-*"):
        if not revision_directory.is_dir():
            continue
        for run_directory in revision_directory.iterdir():
            if run_directory.is_dir():
                index[run_directory.name] = run_directory
    return index


def load_records(roots: ArtifactRoots) -> tuple[ExperimentRecord, ...]:
    paths = _registry_paths(roots)
    fingerprint = tree_fingerprint(paths)

    def build() -> tuple[ExperimentRecord, ...]:
        run_directories = _run_directory_index(roots)
        records: list[ExperimentRecord] = []
        for path in paths:
            try:
                payload = read_json(path)
            except ArtifactParseError:
                continue
            entries = coerce.as_dict_list(payload, "experiments")
            if not entries:
                continue
            for entry in entries:
                experiment_id = coerce.as_str(entry, "experiment_id")
                if not experiment_id:
                    continue
                revision = coerce.as_int(entry, "revision") or 1
                records.append(
                    ExperimentRecord(
                        experiment_id=experiment_id,
                        revision=revision,
                        registry_path=path,
                        registry_name=_registry_name(roots, path),
                        entry=entry,
                        run_directories=run_directories,
                    )
                )
        return tuple(records)

    return _index_cache.resolve(str(roots.experiments), fingerprint, build)


def _resolve_run_directory(
    roots: ArtifactRoots,
    record: ExperimentRecord,
    run: dict[str, Any],
) -> Path | None:
    run_id = coerce.as_str(run, "run_id")
    if not run_id:
        return None
    located = record.run_directories.get(run_id)
    if located is not None and located.is_dir():
        return located
    recorded = coerce.as_str(run, "artifact_directory")
    if not recorded:
        return None
    try:
        candidate = ensure_within(roots.readable_roots, Path(recorded))
    except Exception:
        return None
    return candidate if candidate.is_dir() else None


def _run_entries(record: ExperimentRecord) -> list[dict[str, Any]]:
    return coerce.as_dict_list(record.entry, "runs")


def _evidence_run(record: ExperimentRecord, run_id: str | None = None) -> dict[str, Any] | None:
    runs = _run_entries(record)
    if run_id is not None:
        for run in runs:
            if coerce.as_str(run, "run_id") == run_id:
                return run
        raise ArtifactNotFoundError(f"实验 {record.experiment_id} 不存在运行 {run_id}")
    completed = [run for run in runs if coerce.as_str(run, "status") == RunStatus.COMPLETED.value]
    if completed:
        return completed[-1]
    return runs[-1] if runs else None


def _read_run_artifact(
    roots: ArtifactRoots,
    record: ExperimentRecord,
    run: dict[str, Any],
    artifact_name: str,
) -> dict[str, Any] | None:
    directory = _resolve_run_directory(roots, record, run)
    if directory is None:
        return None
    path = directory / artifact_name
    if not path.is_file():
        return None
    try:
        return read_json(path)
    except (ArtifactNotFoundError, ArtifactParseError):
        return None


def _build_event_definition(payload: dict[str, Any]) -> EventDefinition | None:
    if not payload:
        return None
    return EventDefinition(
        name=coerce.as_str(payload, "name"),
        description=coerce.as_str(payload, "description"),
        combination=coerce.as_str(payload, "combination"),
        conditions=[
            EventCondition(
                left_column=coerce.as_str(condition, "left_column"),
                operator=coerce.as_str(condition, "operator"),
                right_column=coerce.as_str(condition, "right_column"),
                value=condition.get("value"),
                left_lag_bars=coerce.as_int(condition, "left_lag_bars"),
                right_lag_bars=coerce.as_int(condition, "right_lag_bars"),
            )
            for condition in coerce.as_dict_list(payload, "conditions")
        ],
    )


def _build_event_study(config: dict[str, Any]) -> EventStudyView | None:
    raw = coerce.as_dict(config, "event_study")
    if not raw:
        return None
    horizons = [value for value in coerce.as_list(raw, "horizons_bars") if isinstance(value, int)]
    return EventStudyView(
        event=_build_event_definition(coerce.as_dict(raw, "event")),
        eligibility=_build_event_definition(coerce.as_dict(raw, "eligibility")),
        price_column=coerce.as_str(raw, "price_column"),
        high_column=coerce.as_str(raw, "high_column"),
        low_column=coerce.as_str(raw, "low_column"),
        horizons_bars=horizons,
        return_type=coerce.as_str(raw, "return_type"),
        overlap_policy=coerce.as_str(raw, "overlap_policy"),
    )


def _build_distribution(payload: dict[str, Any]) -> DistributionSummary:
    return DistributionSummary(
        count=coerce.as_int(payload, "count"),
        mean=coerce.as_float(payload, "mean"),
        median=coerce.as_float(payload, "median"),
        standard_deviation=coerce.as_float(payload, "standard_deviation"),
        minimum=coerce.as_float(payload, "minimum"),
        maximum=coerce.as_float(payload, "maximum"),
        quantile_05=coerce.as_float(payload, "quantile_05"),
        quantile_25=coerce.as_float(payload, "quantile_25"),
        quantile_75=coerce.as_float(payload, "quantile_75"),
        quantile_95=coerce.as_float(payload, "quantile_95"),
        positive_probability=coerce.as_float(payload, "positive_probability"),
    )


def _build_statistical_report(payload: dict[str, Any] | None) -> StatisticalReport | None:
    if not payload:
        return None
    horizons: list[HorizonStatistics] = []
    for horizon in coerce.as_dict_list(payload, "horizons"):
        interval = coerce.as_float_pair(horizon, "excess_mean_confidence_interval")
        q_value = coerce.as_float(horizon, "adjusted_q_value")
        horizons.append(
            HorizonStatistics(
                horizon_bars=coerce.as_int(horizon, "horizon_bars"),
                event_forward_return=_build_distribution(
                    coerce.as_dict(horizon, "event_forward_return")
                ),
                baseline_forward_return=_build_distribution(
                    coerce.as_dict(horizon, "baseline_forward_return")
                ),
                maximum_upside_return=_build_distribution(
                    coerce.as_dict(horizon, "maximum_upside_return")
                ),
                maximum_downside_return=_build_distribution(
                    coerce.as_dict(horizon, "maximum_downside_return")
                ),
                time_to_first_positive_bar=_build_distribution(
                    coerce.as_dict(horizon, "time_to_first_positive_bar")
                ),
                time_to_first_negative_bar=_build_distribution(
                    coerce.as_dict(horizon, "time_to_first_negative_bar")
                ),
                excess_mean_return=coerce.as_float(horizon, "excess_mean_return"),
                excess_mean_confidence_interval=interval,
                standardized_effect=coerce.as_float(horizon, "standardized_effect"),
                bootstrap_p_value=coerce.as_float(horizon, "bootstrap_p_value"),
                adjusted_q_value=q_value,
                warnings=coerce.as_str_list(horizon, "warnings"),
                confidence_interval_includes_zero=(
                    None if interval is None else interval[0] <= 0.0 <= interval[1]
                ),
                passes_significance_threshold=(
                    None if q_value is None else q_value <= SIGNIFICANCE_THRESHOLD
                ),
            )
        )
    return StatisticalReport(
        experiment_id=coerce.as_str(payload, "experiment_id"),
        revision=coerce.as_int(payload, "revision"),
        config_sha256=coerce.as_str(payload, "config_sha256"),
        expected_direction=coerce.as_str(payload, "expected_direction"),
        confidence_level=coerce.as_float(payload, "confidence_level"),
        bootstrap_method=coerce.as_str(payload, "bootstrap_method"),
        bootstrap_samples=coerce.as_int(payload, "bootstrap_samples"),
        random_seed=coerce.as_int(payload, "random_seed"),
        multiple_testing_adjustment=coerce.as_str(payload, "multiple_testing_adjustment"),
        significance_threshold=SIGNIFICANCE_THRESHOLD,
        horizons=horizons,
        warnings=coerce.as_str_list(payload, "warnings"),
    )


def _build_run_summary(
    roots: ArtifactRoots,
    record: ExperimentRecord,
    run: dict[str, Any],
) -> RunSummary:
    directory = _resolve_run_directory(roots, record, run)
    return RunSummary(
        run_id=coerce.as_required_str(run, "run_id", "unknown"),
        status=coerce.as_str(run, "status"),
        code_version=coerce.as_str(run, "code_version"),
        started_at=coerce.as_datetime(run, "started_at"),
        completed_at=coerce.as_datetime(run, "completed_at"),
        frame_sha256=coerce.as_str(run, "frame_sha256"),
        error=coerce.as_str(run, "error"),
        artifact_directory=(
            relative_to_repository(roots.repository, directory) if directory else None
        ),
        artifacts_available=directory is not None,
    )


def _summarize(roots: ArtifactRoots, record: ExperimentRecord) -> ExperimentSummary:
    entry = record.entry
    runs = _run_entries(record)
    statuses = [coerce.as_str(run, "status") for run in runs]
    evidence = _evidence_run(record)
    config = _read_run_artifact(roots, record, evidence, CONFIG_ARTIFACT) if evidence else None
    dataset_reference = coerce.as_dict(config or {}, "dataset")
    event_study = _build_event_study(config or {})
    return ExperimentSummary(
        experiment_id=record.experiment_id,
        revision=record.revision,
        title=coerce.as_required_str(entry, "title", record.experiment_id),
        hypothesis_statement=coerce.as_str(entry, "hypothesis_statement"),
        conclusion=coerce.as_required_str(
            entry, "conclusion", ExperimentConclusion.NOT_REVIEWED.value
        ),
        conclusion_notes=coerce.as_str(entry, "conclusion_notes"),
        registered_at=coerce.as_datetime(entry, "registered_at"),
        config_sha256=coerce.as_str(entry, "config_sha256"),
        dataset_sha256=coerce.as_str(entry, "dataset_sha256"),
        symbol=coerce.as_str(dataset_reference, "symbol"),
        timeframe=coerce.as_str(dataset_reference, "timeframe"),
        event_name=event_study.event.name if event_study and event_study.event else None,
        horizons_bars=event_study.horizons_bars if event_study else [],
        run_count=len(runs),
        completed_run_count=sum(1 for status in statuses if status == RunStatus.COMPLETED.value),
        failed_run_count=sum(1 for status in statuses if status == RunStatus.FAILED.value),
        latest_run_status=statuses[-1] if statuses else None,
        registry_name=record.registry_name,
    )


def list_experiments(roots: ArtifactRoots) -> list[ExperimentSummary]:
    summaries = [_summarize(roots, record) for record in load_records(roots)]
    return sorted(
        summaries,
        key=lambda summary: (summary.registered_at is not None, summary.registered_at),
        reverse=True,
    )


def find_record(
    roots: ArtifactRoots,
    experiment_id: str,
    revision: int | None = None,
) -> ExperimentRecord:
    matches = [record for record in load_records(roots) if record.experiment_id == experiment_id]
    if not matches:
        raise ArtifactNotFoundError(f"实验不存在：{experiment_id}")
    if revision is None:
        return max(matches, key=lambda record: record.revision)
    for record in matches:
        if record.revision == revision:
            return record
    raise ArtifactNotFoundError(f"实验 {experiment_id} 不存在 revision {revision}")


def get_experiment(
    roots: ArtifactRoots,
    experiment_id: str,
    *,
    revision: int | None = None,
    run_id: str | None = None,
    related_finding_ids: list[str] | None = None,
) -> ExperimentDetail:
    record = find_record(roots, experiment_id, revision)
    summary = _summarize(roots, record)
    evidence = _evidence_run(record, run_id)
    config = _read_run_artifact(roots, record, evidence, CONFIG_ARTIFACT) if evidence else None
    report = (
        _read_run_artifact(roots, record, evidence, STATISTICAL_REPORT_ARTIFACT)
        if evidence
        else None
    )
    manifest = (
        _read_run_artifact(roots, record, evidence, RUN_MANIFEST_ARTIFACT) if evidence else None
    )

    hypothesis_raw = coerce.as_dict(config or {}, "hypothesis")
    hypothesis = (
        HypothesisView(
            statement=coerce.as_str(hypothesis_raw, "statement"),
            rationale=coerce.as_str(hypothesis_raw, "rationale"),
            null_hypothesis=coerce.as_str(hypothesis_raw, "null_hypothesis"),
            alternative_hypothesis=coerce.as_str(hypothesis_raw, "alternative_hypothesis"),
            expected_direction=coerce.as_str(hypothesis_raw, "expected_direction"),
            falsification_criteria=coerce.as_str_list(hypothesis_raw, "falsification_criteria"),
        )
        if hypothesis_raw
        else None
    )

    dataset_raw = coerce.as_dict(config or {}, "dataset")
    dataset_index = datasets.index_by_sha256(roots)
    dataset_checksum = coerce.as_str(dataset_raw, "sha256")
    dataset = (
        DatasetReferenceView(
            path=coerce.as_str(dataset_raw, "path"),
            sha256=dataset_checksum,
            symbol=coerce.as_str(dataset_raw, "symbol"),
            timeframe=coerce.as_str(dataset_raw, "timeframe"),
            sample_start=coerce.as_datetime(dataset_raw, "sample_start"),
            sample_end=coerce.as_datetime(dataset_raw, "sample_end"),
            dataset_id=dataset_index.get(dataset_checksum or ""),
        )
        if dataset_raw
        else None
    )

    feature_raw = coerce.as_dict(config or {}, "feature_dataset")
    feature_dataset = (
        FeatureDatasetView(
            manifest_path=coerce.as_str(feature_raw, "manifest_path"),
            manifest_sha256=coerce.as_str(feature_raw, "manifest_sha256"),
            feature_bundle_sha256=coerce.as_str(feature_raw, "feature_bundle_sha256"),
            source_ohlcv_sha256=coerce.as_str(feature_raw, "source_ohlcv_sha256"),
            validity_column=coerce.as_str(feature_raw, "validity_column"),
        )
        if feature_raw
        else None
    )

    statistics_raw = coerce.as_dict(config or {}, "statistics")
    statistics = (
        StatisticalSpecificationView(
            confidence_level=coerce.as_float(statistics_raw, "confidence_level"),
            bootstrap_method=coerce.as_str(statistics_raw, "bootstrap_method"),
            bootstrap_samples=coerce.as_int(statistics_raw, "bootstrap_samples"),
            block_size=coerce.as_int(statistics_raw, "block_size"),
            random_seed=coerce.as_int(statistics_raw, "random_seed"),
            minimum_sample_size=coerce.as_int(statistics_raw, "minimum_sample_size"),
        )
        if statistics_raw
        else None
    )

    run_integrity = (
        RunIntegrity(
            run_id=coerce.as_str(manifest, "run_id"),
            config_sha256=coerce.as_str(manifest, "config_sha256"),
            dataset_sha256=coerce.as_str(manifest, "dataset_sha256"),
            frame_sha256=coerce.as_str(manifest, "frame_sha256"),
            code_version=coerce.as_str(manifest, "code_version"),
            feature_manifest_sha256=coerce.as_str(manifest, "feature_manifest_sha256"),
            raw_event_count=coerce.as_int(manifest, "raw_event_count"),
            selected_event_count=coerce.as_int(manifest, "selected_event_count"),
            eligible_observation_count=coerce.as_int(manifest, "eligible_observation_count"),
            artifact_sha256={
                str(key): str(value)
                for key, value in coerce.as_dict(manifest, "artifact_sha256").items()
            },
            created_at=coerce.as_datetime(manifest, "created_at"),
        )
        if manifest
        else None
    )

    return ExperimentDetail(
        **summary.model_dump(),
        registry_path=relative_to_repository(roots.repository, record.registry_path),
        hypothesis=hypothesis,
        dataset=dataset,
        feature_dataset=feature_dataset,
        event_study=_build_event_study(config or {}),
        statistics=statistics,
        tags=coerce.as_str_list(config or {}, "tags"),
        evidence_run_id=coerce.as_str(evidence or {}, "run_id"),
        statistical_report=_build_statistical_report(report),
        run_integrity=run_integrity,
        runs=[_build_run_summary(roots, record, run) for run in _run_entries(record)],
        related_finding_ids=related_finding_ids or [],
        config_schema_version=coerce.as_int(config or {}, "schema_version"),
    )


def list_run_artifacts(
    roots: ArtifactRoots,
    experiment_id: str,
    run_id: str,
    *,
    revision: int | None = None,
) -> list[ArtifactFile]:
    record = find_record(roots, experiment_id, revision)
    run = _evidence_run(record, run_id)
    directory = _resolve_run_directory(roots, record, run or {})
    if directory is None:
        raise ArtifactNotFoundError(f"运行 {run_id} 的 artifact 目录不存在")
    manifest = _read_run_artifact(roots, record, run or {}, RUN_MANIFEST_ARTIFACT) or {}
    recorded = coerce.as_dict(manifest, "artifact_sha256")
    files: list[ArtifactFile] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        checksum = recorded.get(path.name)
        files.append(
            ArtifactFile(
                name=path.name,
                size_bytes=path.stat().st_size,
                recorded_sha256=checksum if isinstance(checksum, str) else None,
                is_json=path.suffix.lower() == ".json",
                path=relative_to_repository(roots.repository, path),
            )
        )
    return files


def read_run_artifact(
    roots: ArtifactRoots,
    experiment_id: str,
    run_id: str,
    artifact_name: str,
    *,
    revision: int | None = None,
) -> dict[str, Any]:
    ensure_plain_name(artifact_name)
    if not artifact_name.endswith(".json"):
        raise ArtifactParseError("只能查看 JSON artifact；表格类 artifact 请使用预览端点")
    record = find_record(roots, experiment_id, revision)
    run = _evidence_run(record, run_id)
    directory = _resolve_run_directory(roots, record, run or {})
    if directory is None:
        raise ArtifactNotFoundError(f"运行 {run_id} 的 artifact 目录不存在")
    path = ensure_within(roots.readable_roots, directory / artifact_name)
    return read_json(path)


def index_by_dataset_sha256(roots: ArtifactRoots) -> dict[str, list[str]]:
    """dataset checksum → 使用该数据集的实验 ID 列表。"""

    index: dict[str, list[str]] = {}
    for record in load_records(roots):
        checksum = coerce.as_str(record.entry, "dataset_sha256")
        if checksum:
            index.setdefault(checksum, []).append(record.experiment_id)
    return index
