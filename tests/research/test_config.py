from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from aiquantlab.research.config import load_experiment_config, write_experiment_config
from aiquantlab.research.models import ConditionOperator, EventCondition


def test_resolved_config_round_trip_preserves_fingerprint(experiment_config, tmp_path) -> None:
    path = tmp_path / "experiment.yaml"

    write_experiment_config(experiment_config, path)
    loaded = load_experiment_config(path)

    assert loaded == experiment_config
    assert loaded.fingerprint() == experiment_config.fingerprint()


def test_repository_experiment_configurations_are_valid() -> None:
    paths = sorted(Path("config/experiments").glob("*.yaml"))
    configs = [load_experiment_config(path) for path in paths]

    assert {config.experiment_id for config in configs} == {
        "PHASE3-XAUUSD-BEARISH-001",
        "PHASE3-XAUUSD-BULLISH-001",
        "XAUUSD-BULL-CANDLE-001",
    }
    assert all(config.event_study.horizons_bars == (1, 4, 16) for config in configs)


def test_condition_requires_exactly_one_comparison_target() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        EventCondition(
            left_column="close",
            operator=ConditionOperator.GREATER_THAN,
            right_column="open",
            value=1.0,
        )


def test_condition_rejects_future_lag() -> None:
    with pytest.raises(ValidationError):
        EventCondition(
            left_column="close",
            operator=ConditionOperator.GREATER_THAN,
            value=1.0,
            left_lag_bars=-1,
        )
