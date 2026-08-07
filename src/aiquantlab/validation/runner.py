"""Run a frozen candidate once across predeclared chronological splits."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from aiquantlab.backtest import run_backtest
from aiquantlab.strategies import StrategyCandidate
from aiquantlab.validation.models import (
    CandidateAssessment,
    SplitRole,
    SplitValidationResult,
    ValidationPlan,
    ValidationReport,
)


def _assess_split(
    result: SplitValidationResult,
    *,
    minimum_trades: int,
    require_positive_mean: bool,
    maximum_drawdown: float,
) -> tuple[str, ...]:
    failures: list[str] = []
    if result.primary.trade_count < minimum_trades:
        failures.append("insufficient_primary_trades")
    if result.stress.trade_count < minimum_trades:
        failures.append("insufficient_stress_trades")
    if require_positive_mean:
        if result.primary.mean_trade_return is None or result.primary.mean_trade_return <= 0.0:
            failures.append("non_positive_primary_mean_return")
        if result.stress.mean_trade_return is None or result.stress.mean_trade_return <= 0.0:
            failures.append("non_positive_stress_mean_return")
    if result.primary.maximum_drawdown > maximum_drawdown:
        failures.append("primary_drawdown_limit_exceeded")
    if result.stress.maximum_drawdown > maximum_drawdown:
        failures.append("stress_drawdown_limit_exceeded")
    return tuple(failures)


def run_chronological_validation(
    frame: pd.DataFrame,
    candidate: StrategyCandidate,
    plan: ValidationPlan,
) -> ValidationReport:
    """Evaluate fixed rules without adapting them between splits."""

    if plan.candidate_sha256 != candidate.fingerprint():
        raise ValueError("validation plan references a different strategy candidate")
    stress_execution = plan.primary_execution_model.model_copy(
        update={
            "slippage_bps_per_side": plan.criteria.stress_slippage_bps_per_side,
        }
    )
    results: list[SplitValidationResult] = []
    for split in plan.splits:
        primary = run_backtest(
            frame,
            candidate,
            start=split.start,
            end=split.end,
            execution_model=plan.primary_execution_model,
        ).summary
        stress = run_backtest(
            frame,
            candidate,
            start=split.start,
            end=split.end,
            execution_model=stress_execution,
        ).summary
        provisional = SplitValidationResult(
            split=split,
            primary=primary,
            stress=stress,
            criteria_passed=True,
        )
        failures = _assess_split(
            provisional,
            minimum_trades=plan.criteria.minimum_trades_per_evaluation_split,
            require_positive_mean=plan.criteria.require_positive_mean_return,
            maximum_drawdown=plan.criteria.maximum_drawdown_limit,
        )
        results.append(
            provisional.model_copy(
                update={"criteria_passed": not failures, "failures": failures}
            )
        )

    evaluation_results = [
        result
        for result in results
        if result.split.role in {SplitRole.VALIDATION, SplitRole.FINAL_TEST}
    ]
    insufficient = any(
        "insufficient_primary_trades" in result.failures
        or "insufficient_stress_trades" in result.failures
        for result in evaluation_results
    )
    if not plan.research_gate_passed:
        assessment = CandidateAssessment.NOT_SUPPORTED
    elif insufficient:
        assessment = CandidateAssessment.INCONCLUSIVE
    elif all(result.criteria_passed for result in evaluation_results):
        assessment = CandidateAssessment.SUPPORTED
    else:
        assessment = CandidateAssessment.NOT_SUPPORTED

    return ValidationReport(
        plan_sha256=plan.fingerprint(),
        candidate_sha256=candidate.fingerprint(),
        dataset_sha256=plan.dataset_sha256,
        research_gate_passed=plan.research_gate_passed,
        assessment=assessment,
        split_results=tuple(results),
        warnings=(
            "Historical results do not establish future profitability.",
            "The three splits use one quote source and are not cross-asset validation.",
            (
                "Bid/ask prices model observed spread; latency, market impact, and "
                "broker fills remain unmodeled."
            ),
            "Final-test results must not be used to revise this candidate revision.",
            *(
                (
                    "Research gate failed; this run is a pipeline probe, not "
                    "candidate qualification.",
                )
                if not plan.research_gate_passed
                else ()
            ),
        ),
        generated_at=datetime.now(UTC),
    )
