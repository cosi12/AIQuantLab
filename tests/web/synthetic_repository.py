"""Web 层测试用的合成 artifact 仓库构造器。

测试不依赖仓库里的真实研究产物：真实产物会随研究推进变化，用它们断言等于把
测试绑定到当前研究结论上。这里构造一个最小但结构完整的 artifact 树，覆盖
OHLCV 数据集、feature 数据集、实验 registry、run 目录、finding、strategy
candidate 与 validation 报告。

registry 里刻意写入一个不可达的绝对 artifact_directory 与一次失败运行，用于
验证 Web 层按约定目录结构定位 run 并且不隐藏失败记录。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

OHLCV_DATASET_ID = "xauusd_m15_synthetic"
FEATURE_DATASET_ID = "xauusd_m15_synthetic_features"
EXPERIMENT_ID = "SYN-XAUUSD-M15-001"
RUN_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
FAILED_RUN_ID = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
FINDING_ID = "FND-SYN-001"
CANDIDATE_ID = "CAND-SYN-001"
REPORT_NAME = "synthetic_research_note.md"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_parquet(path: Path, row_count: int = 32) -> tuple[str, int]:
    """写出 parquet 并返回其真实 SHA-256，让完整性校验测试可以断言一致。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    timestamps = pd.date_range("2026-01-05 00:00", periods=row_count, freq="15min", tz="UTC")
    opens = 2_000.0 + np.arange(row_count, dtype=float)
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": opens + 1.0,
            "low": opens - 1.0,
            "close": opens + 0.5,
            "volume": np.full(row_count, 100.0),
        }
    )
    frame.to_parquet(path, engine="pyarrow", index=False)
    return hashlib.sha256(path.read_bytes()).hexdigest(), row_count


def _build_ohlcv_dataset(processed: Path) -> str:
    checksum, row_count = _write_parquet(processed / f"{OHLCV_DATASET_ID}.parquet")
    _write_json(
        processed / f"{OHLCV_DATASET_ID}.parquet.manifest.json",
        {
            "schema_version": 1,
            "data_file": f"{OHLCV_DATASET_ID}.parquet",
            "sha256": checksum,
            "row_count": row_count,
            "columns": ["timestamp", "open", "high", "low", "close", "volume"],
            "created_at": "2026-01-06T00:00:00+00:00",
            "metadata": {
                "symbol": "XAUUSD",
                "source": "synthetic",
                "timeframe": "M15",
                "source_timezone": "UTC",
                "canonical_timezone": "UTC",
                "timestamp_convention": "bar_open",
                "price_basis": "bid",
                "volume_type": "tick_activity",
                "calendar_policy": "gaps_retained",
                "notes": ["合成数据，仅用于测试 Web 层读取逻辑"],
                "created_at": "2026-01-06T00:00:00+00:00",
            },
            "quality_report": {
                "passed": True,
                "row_count": row_count,
                "start": "2026-01-05T00:00:00+00:00",
                "end": "2026-01-05T07:45:00+00:00",
                "expected_candle_count": row_count + 2,
                "missing_candle_count": 2,
                "generated_at": "2026-01-06T00:00:00+00:00",
                "issues": [
                    {
                        "code": "missing_candles",
                        "severity": "warning",
                        "message": "expected timestamps are absent",
                        "count": 2,
                        "samples": ["2026-01-05T08:00:00+00:00"],
                    }
                ],
            },
        },
    )
    return checksum


def _build_feature_dataset(processed: Path, source_checksum: str) -> str:
    checksum, row_count = _write_parquet(processed / f"{FEATURE_DATASET_ID}.parquet")
    _write_json(
        processed / f"{FEATURE_DATASET_ID}.parquet.manifest.json",
        {
            "schema_version": 1,
            "output_file": f"{FEATURE_DATASET_ID}.parquet",
            "output_sha256": checksum,
            "row_count": row_count,
            "source_ohlcv_file": f"{OHLCV_DATASET_ID}.parquet",
            "source_ohlcv_sha256": source_checksum,
            "feature_columns": ["body_fraction"],
            "validity_column": "feature_valid",
            "warm_up_bars": 3,
            "code_version": "test",
            "feature_bundle_sha256": "c" * 64,
            "created_at": "2026-01-06T01:00:00+00:00",
            "feature_bundle": {
                "bundle_id": "SYN-BUNDLE-001",
                "revision": 1,
                "features": [
                    {
                        "name": "body_fraction",
                        "family": "candle_shape",
                        "input_columns": ["open", "high", "low", "close"],
                        "lookback_bars": 0,
                        "uses_current_bar": True,
                        "warm_up_bars": 0,
                        "output_dtype": "float64",
                        "economic_meaning": "实体占全幅比例",
                        "leakage_notes": "仅使用当根已收盘的 K 线",
                    }
                ],
            },
        },
    )
    return checksum


def _build_experiment(experiments: Path, dataset_checksum: str, feature_checksum: str) -> None:
    run_directory = (
        experiments / "synthetic_lab" / "research_runs" / EXPERIMENT_ID / "revision-1" / RUN_ID
    )
    _write_json(
        experiments / "synthetic_lab" / "experiment_registry.json",
        {
            "schema_version": 1,
            "experiments": [
                {
                    "experiment_id": EXPERIMENT_ID,
                    "revision": 1,
                    "title": "合成看涨事件研究",
                    "hypothesis_statement": "合成看涨事件之后的前瞻收益为正。",
                    "conclusion": "not_supported",
                    "conclusion_notes": "证据不支持假设，按契约记为 not_supported。",
                    "registered_at": "2026-01-06T02:00:00+00:00",
                    "config_sha256": "d" * 64,
                    "dataset_sha256": feature_checksum,
                    "runs": [
                        {
                            "run_id": FAILED_RUN_ID,
                            "status": "failed",
                            "code_version": "test",
                            "started_at": "2026-01-06T02:01:00+00:00",
                            "completed_at": "2026-01-06T02:01:30+00:00",
                            "error": "合成失败运行，用于验证界面不会隐藏失败。",
                        },
                        {
                            "run_id": RUN_ID,
                            "status": "completed",
                            "code_version": "test",
                            "started_at": "2026-01-06T02:02:00+00:00",
                            "completed_at": "2026-01-06T02:03:00+00:00",
                            "frame_sha256": "e" * 64,
                            "artifact_directory": "/nonexistent/machine/path/" + RUN_ID,
                        },
                    ],
                }
            ],
        },
    )
    _write_json(
        run_directory / "config.resolved.json",
        {
            "schema_version": 1,
            "experiment_id": EXPERIMENT_ID,
            "revision": 1,
            "title": "合成看涨事件研究",
            "hypothesis": {
                "statement": "合成看涨事件之后的前瞻收益为正。",
                "rationale": "用于验证 Web 层能否完整呈现假设与反证条件。",
                "null_hypothesis": "条件均值等于无条件基准均值。",
                "alternative_hypothesis": "条件均值大于基准均值。",
                "expected_direction": "positive",
                "falsification_criteria": ["超额均值的置信区间包含零。"],
            },
            "dataset": {
                "path": f"data/processed/{FEATURE_DATASET_ID}.parquet",
                "sha256": feature_checksum,
                "symbol": "XAUUSD",
                "timeframe": "M15",
            },
            "feature_dataset": {
                "manifest_path": f"data/processed/{FEATURE_DATASET_ID}.parquet.manifest.json",
                "manifest_sha256": "f" * 64,
                "feature_bundle_sha256": "c" * 64,
                "source_ohlcv_sha256": dataset_checksum,
                "validity_column": "feature_valid",
            },
            "event_study": {
                "event": {
                    "name": "synthetic_bullish",
                    "description": "收盘价高于开盘价。",
                    "combination": "all",
                    "conditions": [
                        {
                            "left_column": "close",
                            "operator": "greater_than",
                            "right_column": "open",
                            "left_lag_bars": 0,
                            "right_lag_bars": 0,
                        }
                    ],
                },
                "price_column": "close",
                "high_column": "high",
                "low_column": "low",
                "horizons_bars": [4, 8],
                "return_type": "log",
                "overlap_policy": "non_overlapping",
            },
            "statistics": {
                "confidence_level": 0.95,
                "bootstrap_method": "stationary_block",
                "bootstrap_samples": 2000,
                "block_size": 8,
                "random_seed": 7,
                "minimum_sample_size": 30,
            },
            "tags": ["synthetic"],
        },
    )
    _write_json(
        run_directory / "statistical_report.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "revision": 1,
            "config_sha256": "d" * 64,
            "expected_direction": "positive",
            "confidence_level": 0.95,
            "bootstrap_method": "stationary_block",
            "bootstrap_samples": 2000,
            "random_seed": 7,
            "multiple_testing_adjustment": "benjamini_hochberg",
            "warnings": ["合成样本量偏小。"],
            "horizons": [
                {
                    "horizon_bars": 4,
                    "event_forward_return": {"count": 40, "mean": 0.0001},
                    "baseline_forward_return": {"count": 120, "mean": 0.00012},
                    "maximum_upside_return": {"count": 40, "mean": 0.0009},
                    "maximum_downside_return": {"count": 40, "mean": -0.0008},
                    "time_to_first_positive_bar": {"count": 40, "mean": 1.5},
                    "time_to_first_negative_bar": {"count": 40, "mean": 1.8},
                    "excess_mean_return": -0.00002,
                    "excess_mean_confidence_interval": [-0.0004, 0.00036],
                    "standardized_effect": -0.004,
                    "bootstrap_p_value": 0.62,
                    "adjusted_q_value": 0.88,
                    "warnings": [],
                },
                {
                    "horizon_bars": 8,
                    "event_forward_return": {"count": 40, "mean": 0.0002},
                    "baseline_forward_return": {"count": 120, "mean": 0.00019},
                    "maximum_upside_return": {"count": 40, "mean": 0.0014},
                    "maximum_downside_return": {"count": 40, "mean": -0.0012},
                    "time_to_first_positive_bar": {"count": 40, "mean": 2.1},
                    "time_to_first_negative_bar": {"count": 40, "mean": 2.4},
                    "excess_mean_return": 0.00001,
                    "excess_mean_confidence_interval": [-0.0005, 0.00052],
                    "standardized_effect": 0.002,
                    "bootstrap_p_value": 0.71,
                    "adjusted_q_value": 0.88,
                    "warnings": ["非重叠抽样后样本量下降。"],
                },
            ],
        },
    )
    _write_json(
        run_directory / "run_manifest.json",
        {
            "run_id": RUN_ID,
            "config_sha256": "d" * 64,
            "dataset_sha256": feature_checksum,
            "frame_sha256": "e" * 64,
            "code_version": "test",
            "feature_manifest_sha256": "f" * 64,
            "raw_event_count": 96,
            "selected_event_count": 40,
            "eligible_observation_count": 120,
            "created_at": "2026-01-06T02:03:00+00:00",
            "artifact_sha256": {
                "config.resolved.json": "1" * 64,
                "statistical_report.json": "2" * 64,
            },
        },
    )


def _build_finding(experiments: Path) -> None:
    base = experiments / "synthetic_lab" / "findings"
    _write_json(
        base / "index.json",
        {
            "schema_version": 1,
            "findings": [
                {
                    "finding_id": FINDING_ID,
                    "title": "合成看涨事件不具备可用优势",
                    "status": "rejected",
                    "created_at": "2026-01-06T03:00:00+00:00",
                }
            ],
        },
    )
    _write_json(
        base / FINDING_ID / "finding.json",
        {
            "schema_version": 1,
            "finding_id": FINDING_ID,
            "revision": 1,
            "title": "合成看涨事件不具备可用优势",
            "status": "rejected",
            "market_behavior_claim": "合成看涨事件之后没有可检出的方向性优势。",
            "evidence_summary": "两个 horizon 的超额均值置信区间均包含零。",
            "economic_rationale": "合成数据不含可利用的结构，这是预期结果。",
            "limitations": ["仅一个合成样本区间。"],
            "explicit_non_claims": ["这不是交易规则。"],
            "human_reviewer_notes": "作为流程测试记录保留。",
            "created_at": "2026-01-06T03:00:00+00:00",
            "source_evidence": {
                "experiment_id": EXPERIMENT_ID,
                "revision": 1,
                "run_id": RUN_ID,
                "config_sha256": "d" * 64,
                "dataset_sha256": "c" * 64,
                "statistical_report_sha256": "2" * 64,
            },
            "applicable_event": {
                "name": "synthetic_bullish",
                "description": "收盘价高于开盘价。",
                "combination": "all",
                "conditions": [
                    {
                        "left_column": "close",
                        "operator": "greater_than",
                        "right_column": "open",
                    }
                ],
            },
        },
    )


def _build_candidate(experiments: Path, feature_checksum: str) -> None:
    base = experiments / "synthetic_lab" / "validation"
    _write_json(
        base / "strategy_candidate.json",
        {
            "schema_version": 1,
            "candidate_id": CANDIDATE_ID,
            "revision": 1,
            "title": "合成看涨事件流程探针",
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "direction": "long",
            "purpose": "pipeline_probe",
            "research_gate_passed": False,
            "source_finding_id": FINDING_ID,
            "source_evidence_sha256": "2" * 64,
            "holding_bars": 4,
            "signal_semantics": "事件在当根收盘确认。",
            "execution_timing": "next_bar_open",
            "assumptions": ["下一根开盘价可成交。"],
            "entry_event": {
                "name": "synthetic_bullish",
                "combination": "all",
                "conditions": [
                    {
                        "left_column": "close",
                        "operator": "greater_than",
                        "right_column": "open",
                    }
                ],
            },
            "position_sizing": {"method": "fixed_fraction", "fraction": 0.01},
            "risk_rules": {"maximum_concurrent_positions": 1},
        },
    )
    _write_json(
        base / "validation_plan.json",
        {
            "plan_id": "PLAN-SYN-001",
            "candidate_sha256": "3" * 64,
            "dataset_sha256": feature_checksum,
            "frozen_before_validation": True,
            "research_gate_passed": False,
            "criteria": {
                "minimum_trades_per_evaluation_split": 30,
                "require_positive_mean_return": True,
                "maximum_drawdown_limit": 0.2,
                "stress_slippage_bps_per_side": 5.0,
            },
            "primary_execution_model": {"slippage_bps_per_side": 1.0},
            "splits": [
                {
                    "name": "development",
                    "role": "development",
                    "start": "2026-01-05T00:00:00+00:00",
                    "end": "2026-01-05T04:00:00+00:00",
                },
                {
                    "name": "holdout",
                    "role": "holdout",
                    "start": "2026-01-05T04:00:00+00:00",
                    "end": "2026-01-05T08:00:00+00:00",
                },
            ],
        },
    )
    _write_json(
        base / "validation_report.json",
        {
            "assessment": "not_supported",
            "research_gate_passed": False,
            "plan_sha256": "4" * 64,
            "candidate_sha256": "3" * 64,
            "dataset_sha256": feature_checksum,
            "generated_at": "2026-01-06T04:00:00+00:00",
            "warnings": ["候选来源发现已被拒绝，本次验证仅作流程检查。"],
            "split_results": [
                {
                    "split": {
                        "name": "holdout",
                        "role": "holdout",
                        "start": "2026-01-05T04:00:00+00:00",
                        "end": "2026-01-05T08:00:00+00:00",
                    },
                    "primary": {
                        "trade_count": 4,
                        "cumulative_return": -0.0012,
                        "mean_trade_return": -0.0003,
                        "win_rate": 0.25,
                        "maximum_drawdown": 0.0015,
                    },
                    "stress": {
                        "trade_count": 4,
                        "cumulative_return": -0.0031,
                        "mean_trade_return": -0.0008,
                        "win_rate": 0.25,
                        "maximum_drawdown": 0.0034,
                    },
                    "criteria_passed": False,
                    "failures": ["insufficient_trades", "non_positive_mean_return"],
                }
            ],
        },
    )
    _write_json(base / "validation_manifest.json", {"code_version": "test"})


def _build_report(reports: Path) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    (reports / REPORT_NAME).write_text(
        "# 合成研究记录\n\n本报告用于验证 Markdown 查看器。\n",
        encoding="utf-8",
    )


def build_repository(root: Path) -> Path:
    """在 root 下构造一个完整的合成 artifact 仓库并返回该根目录。"""

    processed = root / "data" / "processed"
    experiments = root / "experiments"
    processed.mkdir(parents=True, exist_ok=True)
    experiments.mkdir(parents=True, exist_ok=True)

    ohlcv_checksum = _build_ohlcv_dataset(processed)
    feature_checksum = _build_feature_dataset(processed, ohlcv_checksum)
    _build_experiment(experiments, ohlcv_checksum, feature_checksum)
    _build_finding(experiments)
    _build_candidate(experiments, feature_checksum)
    _build_report(root / "reports")
    return root
