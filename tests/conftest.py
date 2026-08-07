from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aiquantlab.data.models import Timeframe
from aiquantlab.research.models import (
    BootstrapMethod,
    ConditionOperator,
    DatasetReference,
    EventCondition,
    EventDefinition,
    EventStudySpecification,
    ExpectedDirection,
    ExperimentConfig,
    HypothesisDefinition,
    StatisticalSpecification,
)


@pytest.fixture
def canonical_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-02 00:00", periods=8, freq="15min", tz="UTC")
    opens = 2_000.0 + np.arange(len(timestamps))
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": opens + 1.0,
            "low": opens - 1.0,
            "close": opens + 0.5,
            "volume": np.full(len(timestamps), 100.0),
        }
    )


@pytest.fixture
def experiment_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="XAUUSD-TEST-001",
        revision=1,
        title="Synthetic bullish candle event",
        hypothesis=HypothesisDefinition(
            statement="Bullish candles have positive conditional forward returns.",
            rationale="Synthetic increasing prices provide a deterministic framework test.",
            null_hypothesis="Conditional mean return equals the unconditional baseline mean.",
            alternative_hypothesis="Conditional mean return is greater than the baseline mean.",
            expected_direction=ExpectedDirection.POSITIVE,
            falsification_criteria=("The conditional effect is not positive.",),
        ),
        dataset=DatasetReference(
            path="data.parquet",
            sha256="0" * 64,
            symbol="XAUUSD",
            timeframe=Timeframe.M15,
        ),
        event_study=EventStudySpecification(
            event=EventDefinition(
                name="bullish_candle",
                description="The current close is greater than the current open.",
                conditions=(
                    EventCondition(
                        left_column="close",
                        operator=ConditionOperator.GREATER_THAN,
                        right_column="open",
                    ),
                ),
            ),
            horizons_bars=(1, 2),
        ),
        statistics=StatisticalSpecification(
            bootstrap_method=BootstrapMethod.IID,
            bootstrap_samples=200,
            random_seed=11,
            minimum_sample_size=2,
        ),
        tags=("synthetic",),
    )
