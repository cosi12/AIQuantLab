"""Event-study calculations for forward market behavior."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from aiquantlab.research.conditions import evaluate_event_definition, required_columns
from aiquantlab.research.exceptions import ResearchContractError
from aiquantlab.research.models import EventOverlapPolicy, EventStudySpecification, ReturnType

OBSERVATION_COLUMNS = (
    "event_timestamp",
    "horizon_bars",
    "entry_price",
    "future_price",
    "forward_return",
    "maximum_upside_return",
    "maximum_downside_return",
    "time_to_first_positive_bar",
    "time_to_first_negative_bar",
)
BASELINE_COLUMNS = ("observation_timestamp", "horizon_bars", "forward_return")


@dataclass(frozen=True, slots=True)
class EventStudyResult:
    observations: pd.DataFrame
    baseline: pd.DataFrame
    raw_event_count: int
    selected_event_count: int
    eligible_observation_count: int
    frame_sha256: str


def dataframe_fingerprint(frame: pd.DataFrame) -> str:
    """Hash values, column order, and dtypes for an in-memory research input."""

    header = json.dumps(
        [(str(column), str(dtype)) for column, dtype in frame.dtypes.items()],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    values = pd.util.hash_pandas_object(frame, index=True).to_numpy(dtype="uint64").tobytes()
    digest = hashlib.sha256()
    digest.update(header)
    digest.update(values)
    return digest.hexdigest()


def _validate_frame(frame: pd.DataFrame, specification: EventStudySpecification) -> None:
    columns = {
        "timestamp",
        specification.price_column,
        specification.high_column,
        specification.low_column,
        *required_columns(specification.event),
    }
    if specification.eligibility is not None:
        columns.update(required_columns(specification.eligibility))
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise ResearchContractError(f"event study input is missing columns: {missing}")

    timestamps = frame["timestamp"]
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype) or str(timestamps.dtype.tz) != "UTC":
        raise ResearchContractError("event study timestamps must be timezone-aware UTC values")
    if timestamps.isna().any() or timestamps.duplicated().any():
        raise ResearchContractError("event study timestamps must be non-null and unique")
    if not timestamps.is_monotonic_increasing:
        raise ResearchContractError("event study timestamps must be ascending")

    price_columns = [
        specification.price_column,
        specification.high_column,
        specification.low_column,
    ]
    numeric = frame.loc[:, price_columns].apply(pd.to_numeric, errors="coerce")
    if (
        numeric.isna().any().any()
        or not np.isfinite(numeric.to_numpy(dtype=float)).all()
        or (numeric <= 0).any().any()
    ):
        raise ResearchContractError("event study prices must be finite positive numbers")


def _select_event_positions(
    positions: NDArray[np.int_],
    *,
    policy: EventOverlapPolicy,
    maximum_horizon: int,
) -> NDArray[np.int_]:
    if policy == EventOverlapPolicy.ALLOW or len(positions) == 0:
        return positions
    selected: list[int] = []
    next_allowed = 0
    for raw_position in positions:
        position = int(raw_position)
        if position >= next_allowed:
            selected.append(position)
            next_allowed = position + maximum_horizon + 1
    return np.asarray(selected, dtype=np.int_)


def _forward_return(entry: float, future: float, return_type: ReturnType) -> float:
    if return_type == ReturnType.LOG:
        return float(np.log(future / entry))
    return float(future / entry - 1.0)


def _first_crossing_bar(returns: NDArray[np.float64], *, positive: bool) -> int | None:
    indices = np.flatnonzero(returns > 0 if positive else returns < 0)
    return int(indices[0] + 1) if len(indices) else None


def run_event_study(
    frame: pd.DataFrame,
    specification: EventStudySpecification,
) -> EventStudyResult:
    """Measure forward outcomes after events; no trade or position semantics are applied."""

    _validate_frame(frame, specification)
    event_mask = evaluate_event_definition(frame, specification.event)
    if specification.eligibility is None:
        eligibility_mask = pd.Series(True, index=frame.index)
    else:
        eligibility_mask = evaluate_event_definition(frame, specification.eligibility)
    event_mask &= eligibility_mask

    raw_positions = np.flatnonzero(event_mask.to_numpy())
    selected_positions = _select_event_positions(
        raw_positions,
        policy=specification.overlap_policy,
        maximum_horizon=max(specification.horizons_bars),
    )
    eligible_positions = np.flatnonzero(eligibility_mask.to_numpy())

    timestamps = frame["timestamp"].array
    prices = frame[specification.price_column].to_numpy(dtype=float)
    highs = frame[specification.high_column].to_numpy(dtype=float)
    lows = frame[specification.low_column].to_numpy(dtype=float)
    observation_rows: list[dict[str, object]] = []
    baseline_rows: list[dict[str, object]] = []

    for horizon in specification.horizons_bars:
        for position in selected_positions[selected_positions + horizon < len(frame)]:
            entry = prices[position]
            future_prices = prices[position + 1 : position + horizon + 1]
            close_returns = future_prices / entry - 1.0
            observation_rows.append(
                {
                    "event_timestamp": timestamps[position],
                    "horizon_bars": horizon,
                    "entry_price": entry,
                    "future_price": prices[position + horizon],
                    "forward_return": _forward_return(
                        entry, prices[position + horizon], specification.return_type
                    ),
                    "maximum_upside_return": float(
                        highs[position + 1 : position + horizon + 1].max() / entry - 1.0
                    ),
                    "maximum_downside_return": float(
                        lows[position + 1 : position + horizon + 1].min() / entry - 1.0
                    ),
                    "time_to_first_positive_bar": _first_crossing_bar(
                        close_returns, positive=True
                    ),
                    "time_to_first_negative_bar": _first_crossing_bar(
                        close_returns, positive=False
                    ),
                }
            )

        for position in eligible_positions[eligible_positions + horizon < len(frame)]:
            baseline_rows.append(
                {
                    "observation_timestamp": timestamps[position],
                    "horizon_bars": horizon,
                    "forward_return": _forward_return(
                        prices[position], prices[position + horizon], specification.return_type
                    ),
                }
            )

    observations = pd.DataFrame(observation_rows, columns=OBSERVATION_COLUMNS)
    baseline = pd.DataFrame(baseline_rows, columns=BASELINE_COLUMNS)
    for column in ("time_to_first_positive_bar", "time_to_first_negative_bar"):
        if column in observations:
            observations[column] = observations[column].astype("Int64")
    return EventStudyResult(
        observations=observations,
        baseline=baseline,
        raw_event_count=len(raw_positions),
        selected_event_count=len(selected_positions),
        eligible_observation_count=len(eligible_positions),
        frame_sha256=dataframe_fingerprint(frame),
    )
