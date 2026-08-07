from __future__ import annotations

import pytest

from aiquantlab.research.event_study import run_event_study
from aiquantlab.research.statistics import benjamini_hochberg, build_statistical_report


def test_statistical_report_is_deterministic(canonical_frame, experiment_config) -> None:
    event_result = run_event_study(canonical_frame, experiment_config.event_study)

    first = build_statistical_report(event_result, experiment_config)
    second = build_statistical_report(event_result, experiment_config)

    assert first == second
    assert len(first.horizons) == 2
    assert first.horizons[0].event_forward_return.positive_probability == 1.0
    assert first.horizons[0].excess_mean_confidence_interval is not None
    assert first.horizons[0].adjusted_q_value is not None
    assert "economic significance" in " ".join(first.warnings)


def test_benjamini_hochberg_preserves_missing_tests() -> None:
    adjusted = benjamini_hochberg([0.01, None, 0.04, 0.03])

    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[1] is None
    assert adjusted[2] == pytest.approx(0.04)
    assert adjusted[3] == pytest.approx(0.04)
