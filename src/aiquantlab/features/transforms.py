"""Pure, causal feature transforms with bar-close research semantics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from aiquantlab.features.models import FeatureSpec


def is_bullish_candle(frame: pd.DataFrame, specification: FeatureSpec) -> pd.Series:
    """Return whether the current, fully closed candle closes above its open."""

    del specification
    valid = frame["open"].notna() & frame["close"].notna()
    result = (frame["close"] > frame["open"]).astype("boolean")
    return result.where(valid, pd.NA)


def body_ratio(frame: pd.DataFrame, specification: FeatureSpec) -> pd.Series:
    """Return signed candle body divided by range; zero ranges are invalid."""

    del specification
    candle_range = frame["high"] - frame["low"]
    valid_range = candle_range.where(candle_range != 0, np.nan)
    return ((frame["close"] - frame["open"]) / valid_range).astype("float64")
