"""Code registry for approved causal feature definitions and transforms."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from aiquantlab.features.exceptions import FeatureRegistryError
from aiquantlab.features.models import (
    FeatureBundle,
    FeatureFamily,
    FeatureOutputDType,
    FeatureSpec,
)
from aiquantlab.features.transforms import body_ratio, is_bullish_candle

FeatureTransform = Callable[[pd.DataFrame, FeatureSpec], pd.Series]


IS_BULLISH_CANDLE = FeatureSpec(
    name="is_bullish_candle",
    family=FeatureFamily.PRICE_STRUCTURE,
    input_columns=("open", "close"),
    lookback_bars=0,
    uses_current_bar=True,
    warm_up_bars=0,
    output_dtype=FeatureOutputDType.BOOLEAN,
    economic_meaning="Whether the current candle has a positive signed body.",
    leakage_notes="Uses the current candle and is valid only after that candle has fully closed.",
)

BODY_RATIO = FeatureSpec(
    name="body_ratio",
    family=FeatureFamily.PRICE_STRUCTURE,
    input_columns=("open", "high", "low", "close"),
    lookback_bars=0,
    uses_current_bar=True,
    warm_up_bars=0,
    output_dtype=FeatureOutputDType.FLOAT64,
    economic_meaning="Signed candle body normalized by the current candle high-low range.",
    leakage_notes="Uses the current candle and is valid only after that candle has fully closed.",
)


class FeatureRegistry:
    """In-memory registry that binds immutable specs to reviewed code transforms."""

    def __init__(self) -> None:
        self._specifications: dict[str, FeatureSpec] = {}
        self._transforms: dict[str, FeatureTransform] = {}

    def register(self, specification: FeatureSpec, transform: FeatureTransform) -> None:
        if specification.name in self._specifications:
            raise FeatureRegistryError(f"feature is already registered: {specification.name}")
        self._specifications[specification.name] = specification
        self._transforms[specification.name] = transform

    def get_specification(self, name: str) -> FeatureSpec:
        try:
            return self._specifications[name]
        except KeyError as exc:
            raise FeatureRegistryError(f"feature is not registered: {name}") from exc

    def get_transform(self, specification: FeatureSpec) -> FeatureTransform:
        registered = self.get_specification(specification.name)
        if registered.fingerprint() != specification.fingerprint():
            raise FeatureRegistryError(
                f"bundle specification differs from registered feature: {specification.name}"
            )
        return self._transforms[specification.name]

    def validate_bundle(self, bundle: FeatureBundle) -> None:
        for specification in bundle.features:
            self.get_transform(specification)


def default_feature_registry() -> FeatureRegistry:
    registry = FeatureRegistry()
    registry.register(IS_BULLISH_CANDLE, is_bullish_candle)
    registry.register(BODY_RATIO, body_ratio)
    return registry


def price_structure_bundle() -> FeatureBundle:
    return FeatureBundle(
        bundle_id="price_structure_v1",
        revision=1,
        features=(IS_BULLISH_CANDLE, BODY_RATIO),
    )

