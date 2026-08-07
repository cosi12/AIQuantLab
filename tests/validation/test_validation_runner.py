from __future__ import annotations

import pandas as pd

from aiquantlab.backtest import ExecutionModel
from aiquantlab.validation import (
    CandidateAssessment,
    ChronologicalSplit,
    SplitRole,
    ValidationCriteria,
    ValidationPlan,
    run_chronological_validation,
)
from tests.backtest.test_engine import candidate, execution_frame


def test_chronological_validation_runs_frozen_candidate_on_all_splits() -> None:
    first = execution_frame()
    second = first.copy()
    second["timestamp"] += pd.Timedelta(days=1)
    third = first.copy()
    third["timestamp"] += pd.Timedelta(days=2)
    frame = pd.concat((first, second, third), ignore_index=True)
    strategy = candidate()
    boundaries = pd.date_range("2024-01-01", periods=4, freq="1D", tz="UTC")
    plan = ValidationPlan(
        plan_id="XAUUSD-VALIDATION-TEST",
        candidate_sha256=strategy.fingerprint(),
        dataset_sha256="b" * 64,
        frozen_before_validation=True,
        research_gate_passed=True,
        splits=(
            ChronologicalSplit(
                name="research-2024-01-01",
                role=SplitRole.RESEARCH,
                start=boundaries[0].to_pydatetime(),
                end=boundaries[1].to_pydatetime(),
            ),
            ChronologicalSplit(
                name="validation-2024-01-02",
                role=SplitRole.VALIDATION,
                start=boundaries[1].to_pydatetime(),
                end=boundaries[2].to_pydatetime(),
            ),
            ChronologicalSplit(
                name="final-2024-01-03",
                role=SplitRole.FINAL_TEST,
                start=boundaries[2].to_pydatetime(),
                end=boundaries[3].to_pydatetime(),
            ),
        ),
        primary_execution_model=ExecutionModel(),
        criteria=ValidationCriteria(
            minimum_trades_per_evaluation_split=1,
            require_positive_mean_return=False,
            maximum_drawdown_limit=1.0,
            stress_slippage_bps_per_side=1.0,
        ),
    )

    report = run_chronological_validation(frame, strategy, plan)

    assert report.assessment == CandidateAssessment.SUPPORTED
    assert len(report.split_results) == 3
    assert all(result.primary.trade_count == 4 for result in report.split_results)
    assert all(result.criteria_passed for result in report.split_results)
