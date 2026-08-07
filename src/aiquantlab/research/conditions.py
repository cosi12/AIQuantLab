"""Causal evaluation of structured event conditions."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from pandas.api.types import is_numeric_dtype

from aiquantlab.research.exceptions import ResearchContractError
from aiquantlab.research.models import (
    ConditionCombination,
    ConditionOperator,
    EventCondition,
    EventDefinition,
)


_OPERATORS: dict[ConditionOperator, Callable[[pd.Series, object], pd.Series]] = {
    ConditionOperator.GREATER_THAN: lambda left, right: left > right,
    ConditionOperator.GREATER_THAN_OR_EQUAL: lambda left, right: left >= right,
    ConditionOperator.LESS_THAN: lambda left, right: left < right,
    ConditionOperator.LESS_THAN_OR_EQUAL: lambda left, right: left <= right,
    ConditionOperator.EQUAL: lambda left, right: left == right,
    ConditionOperator.NOT_EQUAL: lambda left, right: left != right,
}


def required_columns(definition: EventDefinition) -> set[str]:
    columns = {condition.left_column for condition in definition.conditions}
    columns.update(
        condition.right_column
        for condition in definition.conditions
        if condition.right_column is not None
    )
    return columns


def evaluate_condition(frame: pd.DataFrame, condition: EventCondition) -> pd.Series:
    missing = sorted(
        required
        for required in required_columns_for_condition(condition)
        if required not in frame
    )
    if missing:
        raise ResearchContractError(f"event condition references missing columns: {missing}")

    left = frame[condition.left_column].shift(condition.left_lag_bars)
    right: object
    if condition.right_column is not None:
        right_series = frame[condition.right_column].shift(condition.right_lag_bars)
        right = right_series
        valid = left.notna() & right_series.notna()
    else:
        right = condition.value
        valid = left.notna()

    ordered_operators = {
        ConditionOperator.GREATER_THAN,
        ConditionOperator.GREATER_THAN_OR_EQUAL,
        ConditionOperator.LESS_THAN,
        ConditionOperator.LESS_THAN_OR_EQUAL,
    }
    if condition.operator in ordered_operators:
        right_is_numeric = (
            is_numeric_dtype(right.dtype)
            if isinstance(right, pd.Series)
            else isinstance(right, (int, float)) and not isinstance(right, bool)
        )
        if not is_numeric_dtype(left.dtype) or not right_is_numeric:
            raise ResearchContractError("ordered event comparisons require numeric operands")

    try:
        result = _OPERATORS[condition.operator](left, right)
    except (TypeError, ValueError) as exc:
        raise ResearchContractError(
            f"condition {condition.left_column} {condition.operator.value} could not be evaluated"
        ) from exc
    return (result & valid).fillna(False).astype(bool)


def required_columns_for_condition(condition: EventCondition) -> set[str]:
    columns = {condition.left_column}
    if condition.right_column is not None:
        columns.add(condition.right_column)
    return columns


def evaluate_event_definition(frame: pd.DataFrame, definition: EventDefinition) -> pd.Series:
    masks = [evaluate_condition(frame, condition) for condition in definition.conditions]
    result = masks[0].copy()
    for mask in masks[1:]:
        if definition.combination == ConditionCombination.ALL:
            result &= mask
        else:
            result |= mask
    result.name = definition.name
    return result
