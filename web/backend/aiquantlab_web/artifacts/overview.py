"""Dashboard 总览聚合。

总览只汇总规模与状态分布，不做任何有利解读；`latest_results` 使用 artifact 原始状态值。
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from aiquantlab_web.artifacts import candidates, datasets, experiments, findings, reports
from aiquantlab_web.schemas import (
    LatestResult,
    Overview,
    OverviewCounts,
    StatusTally,
    SystemCheck,
)
from aiquantlab_web.settings import ArtifactRoots

_RECENT_EXPERIMENT_LIMIT = 5
_LATEST_RESULT_LIMIT = 5

_NOTICES = (
    "本平台是研究与验证界面，不生成交易信号，也不执行交易。",
    "统计显著性不等于经济显著性，历史结果不构成未来盈利证据。",
    "被拒绝与结论不确定的研究会被永久保留，失败研究同样是知识资产。",
)


def _tally(values: list[str | None], fallback: str) -> list[StatusTally]:
    counter = Counter(value or fallback for value in values)
    return [
        StatusTally(label=label, count=count)
        for label, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _system_checks(roots: ArtifactRoots) -> list[SystemCheck]:
    checks = [
        SystemCheck(
            name=name,
            ok=bool(description["exists"]),
            detail=str(description["path"]),
        )
        for name, description in roots.describe().items()
    ]
    checks.append(
        SystemCheck(
            name="write_access",
            ok=True,
            detail="Web 层为只读，不存在写入端点",
        )
    )
    return checks


def build_overview(roots: ArtifactRoots) -> Overview:
    dataset_summaries = datasets.list_datasets(roots)
    experiment_summaries = experiments.list_experiments(roots)
    finding_summaries = findings.list_findings(roots)
    candidate_summaries = candidates.list_candidates(roots)
    report_summaries = reports.list_reports(roots)

    latest: list[LatestResult] = []
    for finding in finding_summaries:
        latest.append(
            LatestResult(
                kind="finding",
                identifier=finding.finding_id,
                title=finding.title,
                status=finding.status,
                detail=finding.source_experiment_id,
                occurred_at=finding.reviewed_at,
                link=f"/research/findings/{finding.finding_id}",
            )
        )
    for candidate in candidate_summaries:
        latest.append(
            LatestResult(
                kind="candidate",
                identifier=candidate.candidate_id,
                title=candidate.title,
                status=candidate.display_status,
                detail=candidate.validation_assessment,
                occurred_at=candidate.validated_at,
                link=f"/strategies/{candidate.candidate_id}",
            )
        )
    for experiment in experiment_summaries[:_RECENT_EXPERIMENT_LIMIT]:
        latest.append(
            LatestResult(
                kind="experiment",
                identifier=experiment.experiment_id,
                title=experiment.title,
                status=experiment.conclusion,
                detail=experiment.symbol,
                occurred_at=experiment.registered_at,
                link=f"/research/{experiment.experiment_id}",
            )
        )
    latest.sort(
        key=lambda result: (result.occurred_at is not None, result.occurred_at),
        reverse=True,
    )

    return Overview(
        counts=OverviewCounts(
            datasets=len(dataset_summaries),
            experiments=len(experiment_summaries),
            experiment_runs=sum(summary.run_count for summary in experiment_summaries),
            findings=len(finding_summaries),
            strategy_candidates=len(candidate_summaries),
            reports=len(report_summaries),
        ),
        experiments_by_conclusion=_tally(
            [summary.conclusion for summary in experiment_summaries], "not_reviewed"
        ),
        findings_by_status=_tally([summary.status for summary in finding_summaries], "unknown"),
        candidates_by_display_status=_tally(
            [summary.display_status for summary in candidate_summaries], "PENDING_REVIEW"
        ),
        recent_experiments=experiment_summaries[:_RECENT_EXPERIMENT_LIMIT],
        latest_results=latest[:_LATEST_RESULT_LIMIT],
        system_checks=_system_checks(roots),
        dataset_warning_total=sum(summary.warning_count for summary in dataset_summaries),
        notices=list(_NOTICES),
        generated_at=datetime.now(UTC),
    )
