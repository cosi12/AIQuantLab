from __future__ import annotations

import pytest

from aiquantlab.research.event_study import run_event_study
from aiquantlab.research.exceptions import ResearchContractError
from aiquantlab.research.models import EventOverlapPolicy


def test_event_study_measures_forward_behavior_without_trade_semantics(
    canonical_frame,
    experiment_config,
) -> None:
    result = run_event_study(canonical_frame, experiment_config.event_study)

    assert result.raw_event_count == 8
    assert result.selected_event_count == 8
    assert len(result.observations) == 13
    first = result.observations.iloc[0]
    expected_return = canonical_frame.loc[1, "close"] / canonical_frame.loc[0, "close"] - 1
    assert first["forward_return"] == pytest.approx(expected_return)
    assert first["time_to_first_positive_bar"] == 1


def test_non_overlapping_policy_removes_dependent_event_windows(
    canonical_frame,
    experiment_config,
) -> None:
    specification = experiment_config.event_study.model_copy(
        update={"overlap_policy": EventOverlapPolicy.NON_OVERLAPPING}
    )

    result = run_event_study(canonical_frame, specification)

    assert result.raw_event_count == 8
    assert result.selected_event_count == 3
    assert len(result.observations) == 5


def test_event_study_rejects_out_of_order_input(canonical_frame, experiment_config) -> None:
    out_of_order = canonical_frame.iloc[::-1].reset_index(drop=True)

    with pytest.raises(ResearchContractError, match="ascending"):
        run_event_study(out_of_order, experiment_config.event_study)
