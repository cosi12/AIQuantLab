"""读取已发布的 research finding。

被拒绝的 finding 与被接受的 finding 一样保留并可浏览：失败研究是知识资产。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiquantlab_web.artifacts import coerce
from aiquantlab_web.artifacts.cache import FingerprintCache
from aiquantlab_web.artifacts.paths import read_json, relative_to_repository, tree_fingerprint
from aiquantlab_web.errors import ArtifactNotFoundError, ArtifactParseError
from aiquantlab_web.schemas import (
    EventCondition,
    EventDefinition,
    FindingDetail,
    FindingSummary,
    SourceEvidence,
)
from aiquantlab_web.settings import ArtifactRoots

FINDING_ARTIFACT = "finding.json"
_cache: FingerprintCache[tuple[FindingRecord, ...]] = FingerprintCache()


@dataclass(frozen=True)
class FindingRecord:
    finding_id: str
    path: Path
    payload: dict[str, Any]


def _finding_paths(roots: ArtifactRoots) -> list[Path]:
    if not roots.experiments.is_dir():
        return []
    return sorted(
        path
        for path in roots.experiments.rglob(f"findings/*/{FINDING_ARTIFACT}")
        if path.is_file()
    )


def load_records(roots: ArtifactRoots) -> tuple[FindingRecord, ...]:
    paths = _finding_paths(roots)
    fingerprint = tree_fingerprint(paths)

    def build() -> tuple[FindingRecord, ...]:
        records: list[FindingRecord] = []
        for path in paths:
            try:
                payload = read_json(path)
            except ArtifactParseError:
                continue
            finding_id = coerce.as_str(payload, "finding_id") or path.parent.name
            records.append(FindingRecord(finding_id=finding_id, path=path, payload=payload))
        return tuple(records)

    return _cache.resolve(f"{roots.experiments}:findings", fingerprint, build)


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


def _build_source_evidence(payload: dict[str, Any]) -> SourceEvidence:
    raw = coerce.as_dict(payload, "source_evidence")
    return SourceEvidence(
        experiment_id=coerce.as_str(raw, "experiment_id"),
        revision=coerce.as_int(raw, "revision"),
        run_id=coerce.as_str(raw, "run_id"),
        config_sha256=coerce.as_str(raw, "config_sha256"),
        dataset_sha256=coerce.as_str(raw, "dataset_sha256"),
        statistical_report_sha256=coerce.as_str(raw, "statistical_report_sha256"),
        conclusion=coerce.as_str(raw, "conclusion"),
    )


def _summarize(record: FindingRecord) -> FindingSummary:
    payload = record.payload
    evidence = _build_source_evidence(payload)
    event = _build_event_definition(coerce.as_dict(payload, "applicable_event"))
    return FindingSummary(
        finding_id=record.finding_id,
        title=coerce.as_required_str(payload, "title", record.finding_id),
        status=coerce.as_required_str(payload, "status", "unknown"),
        symbol=coerce.as_str(payload, "symbol"),
        timeframe=coerce.as_str(payload, "timeframe"),
        event_name=event.name if event else None,
        source_experiment_id=evidence.experiment_id,
        source_conclusion=evidence.conclusion,
        reviewed_at=coerce.as_datetime(payload, "reviewed_at"),
        limitation_count=len(coerce.as_str_list(payload, "limitations")),
        non_claim_count=len(coerce.as_str_list(payload, "explicit_non_claims")),
    )


def list_findings(roots: ArtifactRoots) -> list[FindingSummary]:
    summaries = [_summarize(record) for record in load_records(roots)]
    return sorted(
        summaries,
        key=lambda summary: (summary.reviewed_at is not None, summary.reviewed_at),
        reverse=True,
    )


def get_finding(
    roots: ArtifactRoots,
    finding_id: str,
    *,
    derived_candidate_ids: list[str] | None = None,
) -> FindingDetail:
    for record in load_records(roots):
        if record.finding_id != finding_id:
            continue
        payload = record.payload
        summary = _summarize(record)
        return FindingDetail(
            **summary.model_dump(),
            market_behavior_claim=coerce.as_str(payload, "market_behavior_claim"),
            evidence_summary=coerce.as_str(payload, "evidence_summary"),
            economic_rationale=coerce.as_str(payload, "economic_rationale"),
            human_reviewer_notes=coerce.as_str(payload, "human_reviewer_notes"),
            limitations=coerce.as_str_list(payload, "limitations"),
            explicit_non_claims=coerce.as_str_list(payload, "explicit_non_claims"),
            applicable_event=_build_event_definition(coerce.as_dict(payload, "applicable_event")),
            source_evidence=_build_source_evidence(payload),
            artifact_path=relative_to_repository(roots.repository, record.path),
            derived_candidate_ids=derived_candidate_ids or [],
        )
    raise ArtifactNotFoundError(f"研究发现不存在：{finding_id}")


def status_by_finding_id(roots: ArtifactRoots) -> dict[str, str]:
    return {
        record.finding_id: coerce.as_required_str(record.payload, "status", "unknown")
        for record in load_records(roots)
    }


def index_by_experiment_id(roots: ArtifactRoots) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for record in load_records(roots):
        evidence = coerce.as_dict(record.payload, "source_evidence")
        experiment_id = coerce.as_str(evidence, "experiment_id")
        if experiment_id:
            index.setdefault(experiment_id, []).append(record.finding_id)
    return index
