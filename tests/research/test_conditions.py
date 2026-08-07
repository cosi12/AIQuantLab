from __future__ import annotations

from aiquantlab.research.conditions import evaluate_event_definition
from aiquantlab.research.models import ConditionOperator, EventCondition, EventDefinition


def test_lagged_condition_uses_only_current_and_prior_rows(canonical_frame) -> None:
    definition = EventDefinition(
        name="close_increased",
        description="Current close is greater than the prior close.",
        conditions=(
            EventCondition(
                left_column="close",
                operator=ConditionOperator.GREATER_THAN,
                right_column="close",
                right_lag_bars=1,
            ),
        ),
    )

    result = evaluate_event_definition(canonical_frame, definition)

    assert not result.iloc[0]
    assert result.iloc[1:].all()


def test_not_equal_condition_does_not_treat_missing_lag_as_event(canonical_frame) -> None:
    definition = EventDefinition(
        name="close_changed",
        description="Current close differs from the prior close.",
        conditions=(
            EventCondition(
                left_column="close",
                operator=ConditionOperator.NOT_EQUAL,
                right_column="close",
                right_lag_bars=1,
            ),
        ),
    )

    result = evaluate_event_definition(canonical_frame, definition)

    assert not result.iloc[0]
    assert result.iloc[1:].all()
