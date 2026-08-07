from __future__ import annotations

import pandas as pd
import pytest

from aiquantlab.features import (
    FEATURE_VALID_COLUMN,
    FeatureBundle,
    FeatureFamily,
    FeatureOutputDType,
    FeatureRegistry,
    FeatureSpec,
    apply_feature_bundle,
    default_feature_registry,
    price_structure_bundle,
)
from aiquantlab.features.transforms import is_bullish_candle


def test_price_structure_features_and_zero_range(canonical_frame) -> None:
    frame = canonical_frame.copy()
    frame.loc[0, ["open", "high", "low", "close"]] = 2_000.0

    result = apply_feature_bundle(
        frame,
        price_structure_bundle(),
        registry=default_feature_registry(),
    )

    assert result["is_bullish_candle"].dtype == pd.BooleanDtype()
    assert not bool(result.loc[0, "is_bullish_candle"])
    assert pd.isna(result.loc[0, "body_ratio"])
    assert not bool(result.loc[0, FEATURE_VALID_COLUMN])
    assert result.loc[1, "body_ratio"] == pytest.approx(0.25)
    assert bool(result.loc[1, FEATURE_VALID_COLUMN])


def test_future_price_mutation_cannot_change_prior_feature_values(canonical_frame) -> None:
    bundle = price_structure_bundle()
    registry = default_feature_registry()
    baseline = apply_feature_bundle(canonical_frame, bundle, registry=registry)
    mutated = canonical_frame.copy()
    mutated.loc[4:, "open"] = 4_000.0
    mutated.loc[4:, "close"] = 4_100.0
    mutated.loc[4:, "high"] = 4_200.0
    mutated.loc[4:, "low"] = 3_900.0

    changed = apply_feature_bundle(mutated, bundle, registry=registry)

    pd.testing.assert_series_equal(
        baseline.loc[:3, "is_bullish_candle"],
        changed.loc[:3, "is_bullish_candle"],
    )
    pd.testing.assert_series_equal(
        baseline.loc[:3, "body_ratio"],
        changed.loc[:3, "body_ratio"],
    )


def test_declared_warm_up_rows_are_invalid(canonical_frame) -> None:
    specification = FeatureSpec(
        name="bullish_warmup_test",
        family=FeatureFamily.PRICE_STRUCTURE,
        input_columns=("open", "close"),
        lookback_bars=2,
        uses_current_bar=True,
        warm_up_bars=2,
        output_dtype=FeatureOutputDType.BOOLEAN,
        economic_meaning="Test-only bullish candle feature with conservative warm-up.",
        leakage_notes="Uses only the closed current candle and no future observations.",
    )
    bundle = FeatureBundle(bundle_id="warmup_test", features=(specification,))
    registry = FeatureRegistry()
    registry.register(specification, is_bullish_candle)

    result = apply_feature_bundle(canonical_frame, bundle, registry=registry)

    assert result["bullish_warmup_test"].iloc[:2].isna().all()
    assert not result[FEATURE_VALID_COLUMN].iloc[:2].any()
    assert result["bullish_warmup_test"].iloc[2:].notna().all()
    assert result[FEATURE_VALID_COLUMN].iloc[2:].all()
