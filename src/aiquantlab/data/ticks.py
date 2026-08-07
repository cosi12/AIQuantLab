"""Strict tick validation and deterministic bid/ask bar aggregation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from aiquantlab.data.exceptions import DataContractError
from aiquantlab.data.models import Timeframe
from aiquantlab.data.storage import file_sha256

TICK_COLUMNS = (
    "timestamp",
    "bid_price",
    "ask_price",
    "bid_volume",
    "ask_volume",
)
EXECUTION_PRICE_COLUMNS = (
    "bid_open",
    "bid_high",
    "bid_low",
    "bid_close",
    "ask_open",
    "ask_high",
    "ask_low",
    "ask_close",
    "spread_open",
    "spread_close",
)


@dataclass(frozen=True, slots=True)
class TickSourceIdentity:
    """Stable identity and observed bounds for an ordered collection of tick files."""

    file_count: int
    row_count: int
    sha256: str
    start: pd.Timestamp
    end: pd.Timestamp


@dataclass(frozen=True, slots=True)
class TickAggregationResult:
    frame: pd.DataFrame
    source: TickSourceIdentity


def _validate_tick_frame(frame: pd.DataFrame, *, source: str) -> None:
    missing = sorted(set(TICK_COLUMNS).difference(frame.columns))
    if missing:
        raise DataContractError(f"tick source {source} is missing columns: {missing}")
    if frame.empty:
        raise DataContractError(f"tick source {source} is empty")

    timestamps = frame["timestamp"]
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype) or str(timestamps.dtype.tz) != "UTC":
        raise DataContractError(f"tick source {source} timestamps must be UTC")
    if timestamps.isna().any():
        raise DataContractError(f"tick source {source} contains missing timestamps")
    if not timestamps.is_monotonic_increasing:
        raise DataContractError(f"tick source {source} timestamps are out of order")

    prices = frame.loc[:, ["bid_price", "ask_price"]]
    numeric = prices.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
        raise DataContractError(f"tick source {source} contains invalid prices")
    if (numeric <= 0).any().any():
        raise DataContractError(f"tick source {source} contains non-positive prices")
    if (numeric["ask_price"] < numeric["bid_price"]).any():
        raise DataContractError(f"tick source {source} contains ask prices below bid prices")


def _aggregate_tick_frame(frame: pd.DataFrame, timeframe: Timeframe) -> pd.DataFrame:
    indexed = frame.set_index("timestamp", drop=True)
    midpoint = (indexed["bid_price"] + indexed["ask_price"]) / 2.0
    grouper = pd.Grouper(
        freq=timeframe.pandas_frequency,
        closed="left",
        label="left",
        origin="epoch",
    )
    grouped = indexed.groupby(grouper, sort=True)
    midpoint_grouped = midpoint.groupby(grouper, sort=True)

    output = midpoint_grouped.ohlc()
    output["volume"] = grouped.size().astype("float64")
    for side in ("bid", "ask"):
        side_ohlc = grouped[f"{side}_price"].ohlc()
        for field in ("open", "high", "low", "close"):
            output[f"{side}_{field}"] = side_ohlc[field]
    output["spread_open"] = output["ask_open"] - output["bid_open"]
    output["spread_close"] = output["ask_close"] - output["bid_close"]
    output = output.loc[output["open"].notna()]
    output.index.name = "timestamp"
    return output.reset_index()


def tick_source_fingerprint(paths: Sequence[str | Path], *, root: str | Path) -> str:
    """Hash ordered relative paths and file contents into one source identity."""

    base = Path(root).resolve()
    digest = hashlib.sha256()
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            relative = path.relative_to(base).as_posix()
        except ValueError as exc:
            message = f"tick file is outside the declared source root: {path}"
            raise DataContractError(message) from exc
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def aggregate_tick_parquet_files(
    paths: Iterable[str | Path],
    *,
    timeframe: Timeframe,
    source_root: str | Path,
) -> TickAggregationResult:
    """Validate ordered Parquet partitions and aggregate midpoint research bars."""

    ordered_paths = tuple(sorted((Path(path) for path in paths), key=lambda path: path.as_posix()))
    if not ordered_paths:
        raise DataContractError("at least one tick Parquet file is required")
    if len(set(path.resolve() for path in ordered_paths)) != len(ordered_paths):
        raise DataContractError("tick source paths must be unique")

    bar_frames: list[pd.DataFrame] = []
    total_rows = 0
    previous_end: pd.Timestamp | None = None
    source_start: pd.Timestamp | None = None
    source_end: pd.Timestamp | None = None
    for path in ordered_paths:
        if path.suffix.lower() != ".parquet" or not path.is_file():
            raise DataContractError(f"tick source is not a Parquet file: {path}")
        frame = pd.read_parquet(path, columns=list(TICK_COLUMNS), engine="pyarrow")
        _validate_tick_frame(frame, source=str(path))
        current_start = pd.Timestamp(frame["timestamp"].iloc[0])
        current_end = pd.Timestamp(frame["timestamp"].iloc[-1])
        if previous_end is not None and current_start < previous_end:
            raise DataContractError("tick partitions overlap or are not chronologically ordered")
        previous_end = current_end
        source_start = current_start if source_start is None else source_start
        source_end = current_end
        total_rows += len(frame)
        bar_frames.append(_aggregate_tick_frame(frame, timeframe))

    combined = pd.concat(bar_frames, ignore_index=True)
    if combined["timestamp"].duplicated().any():
        raise DataContractError("tick partitions produced duplicate bar timestamps")
    combined = combined.sort_values("timestamp", kind="stable").reset_index(drop=True)
    assert source_start is not None and source_end is not None
    identity = TickSourceIdentity(
        file_count=len(ordered_paths),
        row_count=total_rows,
        sha256=tick_source_fingerprint(ordered_paths, root=source_root),
        start=source_start,
        end=source_end,
    )
    return TickAggregationResult(frame=combined, source=identity)
