from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiquantlab.features.models import (
    FeatureBundle,
    FeatureFamily,
    FeatureOutputDType,
    FeatureSpec,
)
from aiquantlab.features.registry import BODY_RATIO, IS_BULLISH_CANDLE


def test_builtin_specs_declare_causality_and_warm_up() -> None:
    for specification in (IS_BULLISH_CANDLE, BODY_RATIO):
        assert specification.lookback_bars == 0
        assert specification.uses_current_bar is True
        assert specification.warm_up_bars == 0
        assert "closed" in specification.leakage_notes


def test_warm_up_must_cover_declared_lookback() -> None:
    with pytest.raises(ValidationError, match="warm_up_bars"):
        FeatureSpec(
            name="invalid_lookback",
            family=FeatureFamily.PRICE_STRUCTURE,
            input_columns=("close",),
            lookback_bars=2,
            uses_current_bar=True,
            warm_up_bars=1,
            output_dtype=FeatureOutputDType.FLOAT64,
            economic_meaning="Test feature with an invalid warm-up declaration.",
            leakage_notes="Test-only declaration that reads no future observations.",
        )


def test_bundle_fingerprint_changes_when_lookback_changes() -> None:
    original = FeatureBundle(
        bundle_id="fingerprint_test",
        features=(IS_BULLISH_CANDLE,),
    )
    changed_spec = IS_BULLISH_CANDLE.model_copy(
        update={"lookback_bars": 1, "warm_up_bars": 1}
    )
    changed = FeatureBundle(
        bundle_id="fingerprint_test",
        features=(changed_spec,),
    )

    assert original.fingerprint() != changed.fingerprint()

