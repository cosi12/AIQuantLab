"""Prepare and run the fixed Phase 3 XAUUSD descriptive pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from aiquantlab.data import (
    DatasetMetadata,
    Timeframe,
    ValidationOptions,
    ingest_csv,
    load_data_source_config,
    resample_ohlcv,
    validate_ohlcv,
    write_processed_dataset,
)
from aiquantlab.data.storage import file_sha256
from aiquantlab.research import (
    ExperimentConclusion,
    ExperimentRegistry,
    load_experiment_config,
    run_experiment,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data/raw/XAUUSD_M5.csv"
SOURCE_CONFIG_PATH = PROJECT_ROOT / "config/pilots/xauusd_m5_small.yaml"
PROCESSED_PATH = PROJECT_ROOT / "data/processed/xauusd_m15_phase3_pilot.parquet"
REGISTRY_PATH = PROJECT_ROOT / "experiments/phase3_xauusd_registry.json"
ARTIFACT_ROOT = PROJECT_ROOT / "experiments/phase3_xauusd_runs"
EXPERIMENT_CONFIG_PATHS = (
    PROJECT_ROOT / "config/experiments/phase3_xauusd_bullish_candle.yaml",
    PROJECT_ROOT / "config/experiments/phase3_xauusd_bearish_candle.yaml",
)
SAMPLE_START = pd.Timestamp("2026-07-13T00:00:00Z")
SAMPLE_END = pd.Timestamp("2026-07-25T00:00:00Z")


def source_code_fingerprint() -> str:
    """Identify the exact local Python implementation used for an uncommitted pilot."""

    digest = hashlib.sha256()
    paths = sorted((PROJECT_ROOT / "src").rglob("*.py"))
    paths.append(Path(__file__).resolve())
    for path in paths:
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return f"source-tree:{digest.hexdigest()}"


def prepare_dataset(*, overwrite: bool) -> dict[str, object]:
    config = load_data_source_config(SOURCE_CONFIG_PATH)
    ingestion = ingest_csv(RAW_PATH, config)
    if not ingestion.quality_report.passed:
        raise RuntimeError("raw XAUUSD M5 ingestion failed validation")

    sample = ingestion.frame.loc[
        (ingestion.frame["timestamp"] >= SAMPLE_START)
        & (ingestion.frame["timestamp"] < SAMPLE_END)
    ].reset_index(drop=True)
    sample_report = validate_ohlcv(
        sample,
        ValidationOptions(timeframe=Timeframe.M5),
    )
    if not sample_report.passed:
        raise RuntimeError("selected XAUUSD M5 sample failed validation")

    m15 = resample_ohlcv(
        sample,
        source_timeframe=Timeframe.M5,
        target_timeframe=Timeframe.M15,
    )
    m15_report = validate_ohlcv(
        m15,
        ValidationOptions(timeframe=Timeframe.M15),
    )
    if not m15_report.passed:
        raise RuntimeError("resampled XAUUSD M15 sample failed validation")

    metadata: DatasetMetadata = ingestion.metadata.model_copy(
        update={
            "timeframe": Timeframe.M15,
            "notes": (
                f"raw_sha256={file_sha256(RAW_PATH)}",
                f"selection=[{SAMPLE_START.isoformat()}, {SAMPLE_END.isoformat()})",
                "M5 time is interpreted as UTC according to the MetaTrader 5 Python API contract",
                "prices are bid OHLC; volume is tick activity, not centralized traded volume",
                "daily and weekend session gaps are retained and reported as warnings",
            ),
        }
    )
    manifest = write_processed_dataset(
        m15,
        PROCESSED_PATH,
        metadata=metadata,
        quality_report=m15_report,
        overwrite=overwrite,
    )
    return {
        "raw_rows": ingestion.quality_report.row_count,
        "raw_missing_candles": ingestion.quality_report.missing_candle_count,
        "sample_m5_rows": sample_report.row_count,
        "sample_m5_missing_candles": sample_report.missing_candle_count,
        "sample_m15_rows": m15_report.row_count,
        "sample_m15_missing_candles": m15_report.missing_candle_count,
        "sample_start": m15_report.start.isoformat() if m15_report.start else None,
        "sample_end": m15_report.end.isoformat() if m15_report.end else None,
        "processed_path": str(PROCESSED_PATH.relative_to(PROJECT_ROOT)),
        "processed_sha256": manifest.sha256,
    }


def run_pilot(*, overwrite: bool, prepare_only: bool) -> dict[str, object]:
    preparation = prepare_dataset(overwrite=overwrite)
    summary: dict[str, object] = {"preparation": preparation, "experiments": []}
    if prepare_only:
        return summary

    registry = ExperimentRegistry(REGISTRY_PATH)
    code_version = source_code_fingerprint()
    experiment_summaries: list[dict[str, object]] = []
    for config_path in EXPERIMENT_CONFIG_PATHS:
        config = load_experiment_config(config_path)
        result = run_experiment(
            config,
            registry=registry,
            artifact_root=ARTIFACT_ROOT,
            code_version=code_version,
            working_directory=PROJECT_ROOT,
        )
        registry.set_conclusion(
            config.experiment_id,
            config.revision,
            conclusion=ExperimentConclusion.INCONCLUSIVE,
            notes=(
                "Phase 3 framework-validation pilot only: one local quote source, "
                "two weeks, no out-of-sample or cross-asset validation."
            ),
        )
        experiment_summaries.append(
            {
                "experiment_id": config.experiment_id,
                "run_id": result.manifest.run_id,
                "raw_event_count": result.manifest.raw_event_count,
                "selected_event_count": result.manifest.selected_event_count,
                "artifact_directory": str(
                    result.artifact_directory.relative_to(PROJECT_ROOT)
                ),
                "horizons": [
                    horizon.model_dump(mode="json")
                    for horizon in result.statistical_report.horizons
                ],
            }
        )
    summary["experiments"] = experiment_summaries
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace the existing processed pilot dataset",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="validate and resample data without running experiments",
    )
    args = parser.parse_args()
    summary = run_pilot(overwrite=args.overwrite, prepare_only=args.prepare_only)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

