from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


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

