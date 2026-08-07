"""读取 strategy candidate 与其 chronological validation 产物。

策略候选不等于交易策略。展示状态由 purpose、research gate、来源 finding 状态与
validation assessment 共同派生，派生规则见 docs/WEB_ARCHITECTURE.md 第 8.3 节。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiquantlab.strategies.models import CandidatePurpose
from aiquantlab.validation.models import CandidateAssessment
from aiquantlab_web.artifacts import coerce, findings
from aiquantlab_web.artifacts.cache import FingerprintCache
from aiquantlab_web.artifacts.paths import read_json, relative_to_repository, tree_fingerprint
from aiquantlab_web.errors import ArtifactNotFoundError, ArtifactParseError
from aiquantlab_web.schemas import (
    ArtifactFile,
    BacktestSummary,
    CandidateDetail,
    CandidateSummary,
    ChronologicalSplit,
    EventCondition,
    EventDefinition,
    PositionSizing,
    RiskRules,
    SplitValidationResult,
    ValidationCriteria,
    ValidationPlan,
    ValidationReport,
)
from aiquantlab_web.settings import ArtifactRoots

CANDIDATE_ARTIFACT = "strategy_candidate.json"
PLAN_ARTIFACT = "validation_plan.json"
REPORT_ARTIFACT = "validation_report.json"
MANIFEST_ARTIFACT = "validation_manifest.json"

DISPLAY_PIPELINE_PROBE = "PIPELINE_PROBE"
DISPLAY_REJECTED = "REJECTED"
DISPLAY_PENDING_REVIEW = "PENDING_REVIEW"
DISPLAY_SUPPORTED = "SUPPORTED"
DISPLAY_NOT_SUPPORTED = "NOT_SUPPORTED"

_cache: FingerprintCache[tuple[CandidateRecord, ...]] = FingerprintCache()


@dataclass(frozen=True)
class CandidateRecord:
    candidate_id: str
    path: Path
    payload: dict[str, Any]

    @property
    def directory(self) -> Path:
        return self.path.parent


def _candidate_paths(roots: ArtifactRoots) -> list[Path]:
    if not roots.experiments.is_dir():
        return []
    return sorted(
        path for path in roots.experiments.rglob(CANDIDATE_ARTIFACT) if path.is_file()
    )


def load_records(roots: ArtifactRoots) -> tuple[CandidateRecord, ...]:
    paths = _candidate_paths(roots)
    fingerprint = tree_fingerprint(paths)

    def build() -> tuple[CandidateRecord, ...]:
        records: list[CandidateRecord] = []
        for path in paths:
            try:
                payload = read_json(path)
            except ArtifactParseError:
                continue
            candidate_id = coerce.as_str(payload, "candidate_id") or path.parent.name
            records.append(CandidateRecord(candidate_id=candidate_id, path=path, payload=payload))
        return tuple(records)

    return _cache.resolve(f"{roots.experiments}:candidates", fingerprint, build)


def _sibling(record: CandidateRecord, name: str) -> dict[str, Any] | None:
    path = record.directory / name
    if not path.is_file():
        return None
    try:
        return read_json(path)
    except (ArtifactNotFoundError, ArtifactParseError):
        return None


def derive_display_status(
    *,
    purpose: str | None,
    source_finding_status: str | None,
    assessment: str | None,
    has_validation_report: bool,
) -> str:
    """按固定优先级派生展示状态。

    PIPELINE_PROBE 优先级最高：这类候选在契约上不可能取得 qualification，
    界面必须先说明这一点，再展示其验证指标。
    """

    if purpose == CandidatePurpose.PIPELINE_PROBE.value:
        return DISPLAY_PIPELINE_PROBE
    if source_finding_status == "rejected":
        return DISPLAY_REJECTED
    if not has_validation_report:
        return DISPLAY_PENDING_REVIEW
    if assessment == CandidateAssessment.SUPPORTED.value:
        return DISPLAY_SUPPORTED
    if assessment == CandidateAssessment.NOT_SUPPORTED.value:
        return DISPLAY_NOT_SUPPORTED
    return DISPLAY_PENDING_REVIEW


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


def _build_split(payload: dict[str, Any]) -> ChronologicalSplit:
    return ChronologicalSplit(
        name=coerce.as_str(payload, "name"),
        role=coerce.as_str(payload, "role"),
        start=coerce.as_datetime(payload, "start"),
        end=coerce.as_datetime(payload, "end"),
    )


def _build_backtest_summary(payload: dict[str, Any]) -> BacktestSummary:
    return BacktestSummary(
        trade_count=coerce.as_int(payload, "trade_count"),
        cumulative_return=coerce.as_float(payload, "cumulative_return"),
        mean_trade_return=coerce.as_float(payload, "mean_trade_return"),
        median_trade_return=coerce.as_float(payload, "median_trade_return"),
        standard_deviation_trade_return=coerce.as_float(
            payload, "standard_deviation_trade_return"
        ),
        win_rate=coerce.as_float(payload, "win_rate"),
        maximum_drawdown=coerce.as_float(payload, "maximum_drawdown"),
        total_execution_cost_return=coerce.as_float(payload, "total_execution_cost_return"),
    )


def _build_validation_plan(
    roots: ArtifactRoots,
    record: CandidateRecord,
    payload: dict[str, Any] | None,
) -> ValidationPlan | None:
    if not payload:
        return None
    criteria_raw = coerce.as_dict(payload, "criteria")
    return ValidationPlan(
        plan_id=coerce.as_str(payload, "plan_id"),
        candidate_sha256=coerce.as_str(payload, "candidate_sha256"),
        dataset_sha256=coerce.as_str(payload, "dataset_sha256"),
        frozen_before_validation=coerce.as_bool(payload, "frozen_before_validation"),
        research_gate_passed=coerce.as_bool(payload, "research_gate_passed"),
        criteria=ValidationCriteria(
            minimum_trades_per_evaluation_split=coerce.as_int(
                criteria_raw, "minimum_trades_per_evaluation_split"
            ),
            require_positive_mean_return=coerce.as_bool(
                criteria_raw, "require_positive_mean_return"
            ),
            maximum_drawdown_limit=coerce.as_float(criteria_raw, "maximum_drawdown_limit"),
            stress_slippage_bps_per_side=coerce.as_float(
                criteria_raw, "stress_slippage_bps_per_side"
            ),
        ),
        primary_execution_model=coerce.as_dict(payload, "primary_execution_model"),
        splits=[_build_split(split) for split in coerce.as_dict_list(payload, "splits")],
        artifact_path=relative_to_repository(roots.repository, record.directory / PLAN_ARTIFACT),
    )


def _build_validation_report(
    roots: ArtifactRoots,
    record: CandidateRecord,
    payload: dict[str, Any] | None,
) -> ValidationReport | None:
    if not payload:
        return None
    results = [
        SplitValidationResult(
            split=_build_split(coerce.as_dict(result, "split")),
            primary=_build_backtest_summary(coerce.as_dict(result, "primary")),
            stress=_build_backtest_summary(coerce.as_dict(result, "stress")),
            criteria_passed=coerce.as_bool(result, "criteria_passed"),
            failures=coerce.as_str_list(result, "failures"),
        )
        for result in coerce.as_dict_list(payload, "split_results")
    ]
    return ValidationReport(
        assessment=coerce.as_str(payload, "assessment"),
        research_gate_passed=coerce.as_bool(payload, "research_gate_passed"),
        plan_sha256=coerce.as_str(payload, "plan_sha256"),
        candidate_sha256=coerce.as_str(payload, "candidate_sha256"),
        dataset_sha256=coerce.as_str(payload, "dataset_sha256"),
        split_results=results,
        warnings=coerce.as_str_list(payload, "warnings"),
        generated_at=coerce.as_datetime(payload, "generated_at"),
        artifact_path=relative_to_repository(roots.repository, record.directory / REPORT_ARTIFACT),
    )


def _summarize(
    record: CandidateRecord,
    finding_statuses: dict[str, str],
) -> CandidateSummary:
    payload = record.payload
    report = _sibling(record, REPORT_ARTIFACT)
    assessment = coerce.as_str(report or {}, "assessment")
    purpose = coerce.as_str(payload, "purpose")
    source_finding_id = coerce.as_str(payload, "source_finding_id")
    source_finding_status = finding_statuses.get(source_finding_id or "")
    event = _build_event_definition(coerce.as_dict(payload, "entry_event"))
    return CandidateSummary(
        candidate_id=record.candidate_id,
        revision=coerce.as_int(payload, "revision") or 1,
        title=coerce.as_required_str(payload, "title", record.candidate_id),
        symbol=coerce.as_str(payload, "symbol"),
        timeframe=coerce.as_str(payload, "timeframe"),
        direction=coerce.as_str(payload, "direction"),
        purpose=purpose,
        research_gate_passed=coerce.as_bool(payload, "research_gate_passed"),
        source_finding_id=source_finding_id,
        source_finding_status=source_finding_status,
        source_evidence_sha256=coerce.as_str(payload, "source_evidence_sha256"),
        validation_assessment=assessment,
        validated_at=coerce.as_datetime(report or {}, "generated_at"),
        display_status=derive_display_status(
            purpose=purpose,
            source_finding_status=source_finding_status,
            assessment=assessment,
            has_validation_report=report is not None,
        ),
        holding_bars=coerce.as_int(payload, "holding_bars"),
        entry_event_name=event.name if event else None,
        validated=report is not None,
    )


def list_candidates(roots: ArtifactRoots) -> list[CandidateSummary]:
    statuses = findings.status_by_finding_id(roots)
    return [_summarize(record, statuses) for record in load_records(roots)]


def get_candidate(roots: ArtifactRoots, candidate_id: str) -> CandidateDetail:
    statuses = findings.status_by_finding_id(roots)
    for record in load_records(roots):
        if record.candidate_id != candidate_id:
            continue
        payload = record.payload
        summary = _summarize(record, statuses)
        sizing = coerce.as_dict(payload, "position_sizing")
        risk = coerce.as_dict(payload, "risk_rules")
        ledgers = [
            ArtifactFile(
                name=path.name,
                size_bytes=path.stat().st_size,
                recorded_sha256=None,
                is_json=False,
                path=relative_to_repository(roots.repository, path),
            )
            for path in sorted(record.directory.glob("trades_*.parquet"))
        ]
        return CandidateDetail(
            **summary.model_dump(),
            signal_semantics=coerce.as_str(payload, "signal_semantics"),
            execution_timing=coerce.as_str(payload, "execution_timing"),
            entry_event=_build_event_definition(coerce.as_dict(payload, "entry_event")),
            position_sizing=PositionSizing(
                method=coerce.as_str(sizing, "method"),
                fraction=coerce.as_float(sizing, "fraction"),
            ),
            risk_rules=RiskRules(
                maximum_concurrent_positions=coerce.as_int(
                    risk, "maximum_concurrent_positions"
                ),
                stop_loss_fraction=coerce.as_float(risk, "stop_loss_fraction"),
                take_profit_fraction=coerce.as_float(risk, "take_profit_fraction"),
            ),
            assumptions=coerce.as_str_list(payload, "assumptions"),
            validation_plan=_build_validation_plan(
                roots, record, _sibling(record, PLAN_ARTIFACT)
            ),
            validation_report=_build_validation_report(
                roots, record, _sibling(record, REPORT_ARTIFACT)
            ),
            validation_manifest=_sibling(record, MANIFEST_ARTIFACT),
            trade_ledgers=ledgers,
            artifact_path=relative_to_repository(roots.repository, record.path),
            artifact_directory=relative_to_repository(roots.repository, record.directory),
        )
    raise ArtifactNotFoundError(f"策略候选不存在：{candidate_id}")


def index_by_finding_id(roots: ArtifactRoots) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for record in load_records(roots):
        finding_id = coerce.as_str(record.payload, "source_finding_id")
        if finding_id:
            index.setdefault(finding_id, []).append(record.candidate_id)
    return index
