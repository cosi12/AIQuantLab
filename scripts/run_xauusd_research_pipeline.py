"""Run the first frozen XAUUSD research-to-validation pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from aiquantlab.backtest import ExecutionModel, run_backtest
from aiquantlab.data import (
    CalendarPolicy,
    DatasetMetadata,
    PriceBasis,
    Timeframe,
    ValidationOptions,
    VolumeType,
    aggregate_tick_parquet_files,
    read_processed_dataset,
    validate_ohlcv,
    write_processed_dataset,
)
from aiquantlab.data.storage import file_sha256
from aiquantlab.features import (
    default_feature_registry,
    materialize_features,
    price_structure_bundle,
    read_materialized_features,
)
from aiquantlab.findings import FindingRegistry, FindingStatus, promote_finding
from aiquantlab.research import (
    BootstrapMethod,
    ConditionOperator,
    DatasetReference,
    EventCondition,
    EventDefinition,
    EventOverlapPolicy,
    EventStudySpecification,
    ExpectedDirection,
    ExperimentConclusion,
    ExperimentConfig,
    ExperimentRegistry,
    FeatureDatasetReference,
    HypothesisDefinition,
    StatisticalSpecification,
    run_experiment,
)
from aiquantlab.strategies import (
    CandidatePurpose,
    PositionSizingRule,
    StrategyCandidate,
    StrategyDirection,
)
from aiquantlab.validation import (
    ChronologicalSplit,
    SplitRole,
    ValidationCriteria,
    ValidationPlan,
    run_chronological_validation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config/pipelines/xauusd_m15_first.yaml"
PIPELINE_ROOT = PROJECT_ROOT / "experiments/xauusd_m15_first_pipeline"
EXPERIMENT_REGISTRY_PATH = PIPELINE_ROOT / "experiment_registry.json"
EXPERIMENT_RUN_ROOT = PIPELINE_ROOT / "research_runs"
FINDING_INDEX_PATH = PIPELINE_ROOT / "findings/index.json"
FINDING_ROOT = PIPELINE_ROOT / "findings"
VALIDATION_ROOT = PIPELINE_ROOT / "validation"
REPORT_PATH = PROJECT_ROOT / "reports/xauusd_m15_first_pipeline.md"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload: Any = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"configuration must be a mapping: {path}")
    return payload


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def source_code_fingerprint(config_path: Path) -> str:
    """Identify code and the fixed pipeline configuration used for this run."""

    digest = hashlib.sha256()
    paths = sorted((PROJECT_ROOT / "src").rglob("*.py"))
    paths.extend((Path(__file__).resolve(), config_path.resolve()))
    for path in paths:
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"source-tree:{digest.hexdigest()}"


def _prepare_bars(config: dict[str, Any]) -> tuple[pd.DataFrame, str, dict[str, object]]:
    output_path = _project_path(str(config["processed_dataset"]))
    if output_path.exists():
        frame, manifest = read_processed_dataset(output_path)
        note_values = {
            key: value
            for note in manifest.metadata.notes
            if "=" in note
            for key, value in (note.split("=", 1),)
        }
        return frame, manifest.sha256, {
            "reused": True,
            "path": _relative(output_path),
            "sha256": manifest.sha256,
            "rows": len(frame),
            "source_tree_sha256": note_values.get("source_tree_sha256"),
            "source_files": int(note_values["source_file_count"]),
            "source_ticks": int(note_values["source_tick_count"]),
        }

    source = config["source"]
    source_root = _project_path(str(source["directory"]))
    paths = sorted(source_root.glob(str(source["pattern"])))
    aggregation = aggregate_tick_parquet_files(
        paths,
        timeframe=Timeframe.M15,
        source_root=source_root,
    )
    quality = validate_ohlcv(
        aggregation.frame,
        ValidationOptions(
            timeframe=Timeframe.M15,
            calendar_policy=CalendarPolicy.WEEKDAYS,
        ),
    )
    if not quality.passed:
        raise RuntimeError("aggregated XAUUSD M15 bars failed canonical validation")
    metadata = DatasetMetadata(
        symbol=str(config["symbol"]),
        source=str(source["provider"]),
        timeframe=Timeframe.M15,
        price_basis=PriceBasis.MID,
        volume_type=VolumeType.TICK,
        calendar_policy=CalendarPolicy.WEEKDAYS,
        notes=(
            f"source_tree_sha256={aggregation.source.sha256}",
            f"source_file_count={aggregation.source.file_count}",
            f"source_tick_count={aggregation.source.row_count}",
            "OHLC research prices are quote midpoints; execution fields retain bid and ask.",
            "Volume is quote tick count, not centralized traded volume.",
            "Observed session gaps are retained; no bars are filled or interpolated.",
        ),
    )
    manifest = write_processed_dataset(
        aggregation.frame,
        output_path,
        metadata=metadata,
        quality_report=quality,
    )
    return aggregation.frame, manifest.sha256, {
        "reused": False,
        "path": _relative(output_path),
        "sha256": manifest.sha256,
        "rows": len(aggregation.frame),
        "source_tree_sha256": aggregation.source.sha256,
        "source_files": aggregation.source.file_count,
        "source_ticks": aggregation.source.row_count,
        "source_start": aggregation.source.start.isoformat(),
        "source_end": aggregation.source.end.isoformat(),
        "missing_weekday_bars": quality.missing_candle_count,
    }


def _prepare_features(
    config: dict[str, Any],
    *,
    code_version: str,
) -> tuple[pd.DataFrame, object, dict[str, object]]:
    source_path = _project_path(str(config["processed_dataset"]))
    output_path = _project_path(str(config["feature_dataset"]))
    if output_path.exists():
        frame, manifest = read_materialized_features(output_path)
        return frame, manifest, {
            "reused": True,
            "path": _relative(output_path),
            "sha256": manifest.output_sha256,
            "bundle_sha256": manifest.feature_bundle_sha256,
        }
    result = materialize_features(
        source_path,
        output_path,
        price_structure_bundle(),
        registry=default_feature_registry(),
        code_version=code_version,
    )
    return result.frame, result.manifest, {
        "reused": False,
        "path": _relative(output_path),
        "sha256": result.manifest.output_sha256,
        "bundle_sha256": result.manifest.feature_bundle_sha256,
    }


def _strong_bullish_event(config: dict[str, Any]) -> EventDefinition:
    threshold = float(config["research"]["body_ratio_threshold"])
    return EventDefinition(
        name="strong_bullish_candle",
        description="A fully closed bullish M15 candle with a large positive body-to-range ratio.",
        conditions=(
            EventCondition(
                left_column="is_bullish_candle",
                operator=ConditionOperator.EQUAL,
                value=True,
            ),
            EventCondition(
                left_column="body_ratio",
                operator=ConditionOperator.GREATER_THAN_OR_EQUAL,
                value=threshold,
            ),
        ),
    )


def _experiment_config(
    config: dict[str, Any],
    *,
    feature_manifest: Any,
) -> ExperimentConfig:
    research = config["research"]
    research_split = config["splits"]["research"]
    feature_path = _project_path(str(config["feature_dataset"]))
    feature_manifest_path = feature_path.with_suffix(feature_path.suffix + ".manifest.json")
    event = _strong_bullish_event(config)
    horizon = int(research["horizon_bars"])
    return ExperimentConfig(
        schema_version=2,
        experiment_id=str(research["experiment_id"]),
        revision=int(research["revision"]),
        title="XAUUSD M15 behavior after a strong bullish candle",
        hypothesis=HypothesisDefinition(
            statement=(
                "Strong bullish XAUUSD M15 candles are followed by positive four-bar "
                "conditional midpoint returns in the fixed 2015 research sample."
            ),
            rationale=(
                "A large directional candle may represent short-horizon continuation, while "
                "the independent periods determine whether that behavior is tradeable."
            ),
            null_hypothesis=(
                "The conditional mean four-bar return is no greater than the unconditional mean."
            ),
            alternative_hypothesis=(
                "The conditional mean four-bar return exceeds the unconditional mean."
            ),
            expected_direction=ExpectedDirection.POSITIVE,
            falsification_criteria=(
                "The excess mean return is non-positive.",
                "The 95% bootstrap confidence interval includes zero.",
                "The adjusted q-value exceeds 0.05.",
            ),
        ),
        dataset=DatasetReference(
            path=_relative(feature_path),
            sha256=feature_manifest.output_sha256,
            symbol=str(config["symbol"]),
            timeframe=Timeframe.M15,
            sample_start=pd.Timestamp(research_split["start"]).to_pydatetime(),
            sample_end=pd.Timestamp(research_split["end"]).to_pydatetime(),
        ),
        feature_dataset=FeatureDatasetReference(
            manifest_path=_relative(feature_manifest_path),
            manifest_sha256=file_sha256(feature_manifest_path),
            feature_bundle_sha256=feature_manifest.feature_bundle_sha256,
            source_ohlcv_sha256=feature_manifest.source_ohlcv_sha256,
            validity_column=feature_manifest.validity_column,
        ),
        event_study=EventStudySpecification(
            event=event,
            eligibility=EventDefinition(
                name="valid_features",
                description="All registered causal feature values are available for this bar.",
                conditions=(
                    EventCondition(
                        left_column=feature_manifest.validity_column,
                        operator=ConditionOperator.EQUAL,
                        value=True,
                    ),
                ),
            ),
            horizons_bars=(horizon,),
            overlap_policy=EventOverlapPolicy.NON_OVERLAPPING,
        ),
        statistics=StatisticalSpecification(
            bootstrap_method=BootstrapMethod.MOVING_BLOCK,
            bootstrap_samples=int(research["bootstrap_samples"]),
            block_size=int(research["block_size"]),
            random_seed=int(research["random_seed"]),
            minimum_sample_size=int(research["minimum_sample_size"]),
        ),
        tags=("xauusd", "m15", "first-complete-pipeline", "prespecified"),
    )


def _review_and_promote(
    config: dict[str, Any],
    experiment_config: ExperimentConfig,
    experiment_registry: ExperimentRegistry,
    run_id: str,
    report_path: Path,
) -> tuple[Any, Path]:
    review_path = _project_path(str(config["review"]))
    if not review_path.is_file():
        raise FileNotFoundError(
            f"research review is required before strategy generation: {review_path}"
        )
    review = _load_yaml(review_path)
    report_sha256 = file_sha256(report_path)
    if str(review["statistical_report_sha256"]) != report_sha256:
        raise ValueError("review references a different statistical report")
    conclusion = ExperimentConclusion(str(review["conclusion"]))
    experiment_registry.set_conclusion(
        experiment_config.experiment_id,
        experiment_config.revision,
        conclusion=conclusion,
        notes=str(review["conclusion_notes"]),
    )
    finding_status = FindingStatus(str(review["finding"]["status"]))
    finding_registry = FindingRegistry(FINDING_INDEX_PATH, FINDING_ROOT)
    finding_id = str(review["finding"]["finding_id"])
    existing = next(
        (
            item
            for item in finding_registry.list_findings()
            if item.finding_id == finding_id
        ),
        None,
    )
    if existing is not None:
        evidence = existing.source_evidence
        if (
            evidence.config_sha256 != experiment_config.fingerprint()
            or evidence.statistical_report_sha256 != report_sha256
            or existing.status != finding_status
        ):
            raise ValueError("existing finding does not match the reviewed evidence")
        return existing, review_path
    finding = promote_finding(
        registry=experiment_registry,
        finding_registry=finding_registry,
        config=experiment_config,
        run_id=run_id,
        statistical_report_path=report_path,
        finding_id=finding_id,
        title=str(review["finding"]["title"]),
        status=finding_status,
        market_behavior_claim=str(review["finding"]["market_behavior_claim"]),
        applicable_event=experiment_config.event_study.event,
        evidence_summary=str(review["finding"]["evidence_summary"]),
        limitations=tuple(str(item) for item in review["finding"]["limitations"]),
        economic_rationale=str(review["finding"]["economic_rationale"]),
        explicit_non_claims=tuple(
            str(item) for item in review["finding"]["explicit_non_claims"]
        ),
        human_reviewer_notes=str(review["finding"]["human_reviewer_notes"]),
    )
    return finding, review_path


def _candidate(config: dict[str, Any], finding: Any) -> StrategyCandidate:
    strategy = config["strategy"]
    research_gate_passed = finding.status == FindingStatus.ACCEPTED_FOR_RESEARCH
    return StrategyCandidate(
        candidate_id=str(strategy["candidate_id"]),
        revision=int(strategy["revision"]),
        title="Long XAUUSD after a strong bullish M15 candle",
        source_finding_id=finding.finding_id,
        source_evidence_sha256=finding.source_evidence.statistical_report_sha256,
        research_gate_passed=research_gate_passed,
        purpose=(
            CandidatePurpose.QUALIFICATION
            if research_gate_passed
            else CandidatePurpose.PIPELINE_PROBE
        ),
        symbol=str(config["symbol"]),
        timeframe=Timeframe.M15,
        direction=StrategyDirection(str(strategy["direction"])),
        entry_event=finding.applicable_event,
        holding_bars=int(strategy["holding_bars"]),
        position_sizing=PositionSizingRule(fraction=float(strategy["notional_fraction"])),
        assumptions=(
            "Signals are evaluated only after the M15 signal bar closes.",
            "Entries occur at the next observed ask open and exits at the bid open.",
            "The historical bid/ask spread is paid and no spread reconstruction is used.",
            "Holding periods count observed bars, including across session gaps.",
            "Stop loss and take profit are disabled to avoid ambiguous intrabar ordering.",
            "Fixed-fraction notional sizing is a normalized research abstraction, not broker lots.",
            *(
                ("The source finding was rejected; this candidate is only a pipeline probe.",)
                if not research_gate_passed
                else ()
            ),
        ),
    )


def _validation_plan(
    config: dict[str, Any],
    candidate: StrategyCandidate,
    dataset_sha256: str,
) -> ValidationPlan:
    validation = config["validation"]
    roles = (
        ("research", SplitRole.RESEARCH),
        ("validation", SplitRole.VALIDATION),
        ("final_test", SplitRole.FINAL_TEST),
    )
    splits = tuple(
        ChronologicalSplit(
            name=name,
            role=role,
            start=pd.Timestamp(config["splits"][name]["start"]).to_pydatetime(),
            end=pd.Timestamp(config["splits"][name]["end"]).to_pydatetime(),
        )
        for name, role in roles
    )
    return ValidationPlan(
        plan_id=f"{config['pipeline_id']}-VALIDATION",
        candidate_sha256=candidate.fingerprint(),
        dataset_sha256=dataset_sha256,
        frozen_before_validation=True,
        research_gate_passed=candidate.research_gate_passed,
        splits=splits,
        primary_execution_model=ExecutionModel(
            slippage_bps_per_side=float(validation["primary_slippage_bps_per_side"]),
        ),
        criteria=ValidationCriteria(
            minimum_trades_per_evaluation_split=int(
                validation["minimum_trades_per_evaluation_split"]
            ),
            require_positive_mean_return=True,
            maximum_drawdown_limit=float(validation["maximum_drawdown_limit"]),
            stress_slippage_bps_per_side=float(
                validation["stress_slippage_bps_per_side"]
            ),
        ),
    )


def _write_validation_artifacts(
    frame: pd.DataFrame,
    candidate: StrategyCandidate,
    plan: ValidationPlan,
    report: Any,
    *,
    code_version: str,
    pipeline_config_path: Path,
) -> dict[str, str]:
    if VALIDATION_ROOT.exists():
        manifest_path = VALIDATION_ROOT / "validation_manifest.json"
        report_path = VALIDATION_ROOT / "validation_report.json"
        if not manifest_path.is_file() or not report_path.is_file():
            raise FileExistsError("validation directory exists without complete artifacts")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_identity = {
            "candidate_sha256": candidate.fingerprint(),
            "plan_sha256": plan.fingerprint(),
            "dataset_sha256": plan.dataset_sha256,
        }
        if any(manifest.get(key) != value for key, value in expected_identity.items()):
            raise ValueError("existing validation artifacts use a different frozen identity")
        for name, checksum in manifest["artifacts"].items():
            if file_sha256(VALIDATION_ROOT / name) != checksum:
                raise ValueError(f"existing validation artifact checksum failed: {name}")
        stored_report = json.loads(report_path.read_text(encoding="utf-8"))
        current_report = report.model_dump(mode="json")
        stored_report.pop("generated_at", None)
        current_report.pop("generated_at", None)
        if stored_report != current_report:
            raise ValueError("recomputed validation metrics differ from immutable report")
        artifacts = dict(manifest["artifacts"])
        artifacts[manifest_path.name] = file_sha256(manifest_path)
        return artifacts

    VALIDATION_ROOT.mkdir(parents=True, exist_ok=False)
    candidate_path = VALIDATION_ROOT / "strategy_candidate.json"
    plan_path = VALIDATION_ROOT / "validation_plan.json"
    report_path = VALIDATION_ROOT / "validation_report.json"
    candidate_path.write_text(candidate.model_dump_json(indent=2), encoding="utf-8")
    plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    stress_execution = plan.primary_execution_model.model_copy(
        update={"slippage_bps_per_side": plan.criteria.stress_slippage_bps_per_side}
    )
    for split_result in report.split_results:
        for label, execution in (
            ("primary", plan.primary_execution_model),
            ("stress", stress_execution),
        ):
            result = run_backtest(
                frame,
                candidate,
                start=split_result.split.start,
                end=split_result.split.end,
                execution_model=execution,
            )
            expected = split_result.primary if label == "primary" else split_result.stress
            if result.summary != expected:
                raise RuntimeError("trade ledger summary differs from validation report")
            trades_path = VALIDATION_ROOT / f"trades_{split_result.split.name}_{label}.parquet"
            pd.DataFrame(
                [trade.model_dump(mode="json") for trade in result.trades]
            ).to_parquet(trades_path, index=False, engine="pyarrow")

    artifacts = {
        path.name: file_sha256(path)
        for path in sorted(VALIDATION_ROOT.glob("*"))
        if path.is_file()
    }
    manifest_path = VALIDATION_ROOT / "validation_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pipeline_id": config_id_from_plan(plan),
                "code_version": code_version,
                "pipeline_config_sha256": file_sha256(pipeline_config_path),
                "candidate_sha256": candidate.fingerprint(),
                "plan_sha256": plan.fingerprint(),
                "dataset_sha256": plan.dataset_sha256,
                "artifacts": artifacts,
                "created_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    artifacts[manifest_path.name] = file_sha256(manifest_path)
    return artifacts


def config_id_from_plan(plan: ValidationPlan) -> str:
    suffix = "-VALIDATION"
    return plan.plan_id[: -len(suffix)] if plan.plan_id.endswith(suffix) else plan.plan_id


def _format_percentage(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.4f}%"


def _write_markdown_report(
    config: dict[str, Any],
    experiment_result: Any,
    finding: Any,
    candidate: StrategyCandidate,
    validation_report: Any,
    bar_summary: dict[str, object],
    feature_summary: dict[str, object],
) -> None:
    horizon = experiment_result.statistical_report.horizons[0]
    rows = []
    for result in validation_report.split_results:
        rows.append(
            "| {name} | {trades} | {mean} | {ret} | {dd} | {stress} | {passed} |".format(
                name=result.split.name,
                trades=result.primary.trade_count,
                mean=_format_percentage(result.primary.mean_trade_return),
                ret=_format_percentage(result.primary.cumulative_return),
                dd=_format_percentage(result.primary.maximum_drawdown),
                stress=_format_percentage(result.stress.mean_trade_return),
                passed="yes" if result.criteria_passed else "no",
            )
        )
    threshold = config["research"]["body_ratio_threshold"]
    research_horizon = config["research"]["horizon_bars"]
    holding_bars = candidate.holding_bars
    stress_slippage = config["validation"]["stress_slippage_bps_per_side"]
    minimum_trades = config["validation"]["minimum_trades_per_evaluation_split"]
    drawdown_limit = _format_percentage(
        float(config["validation"]["maximum_drawdown_limit"])
    )
    content = f"""# First Complete XAUUSD Research Pipeline

Generated: {datetime.now(UTC).isoformat()}  
Pipeline: `{config['pipeline_id']}`  
Validation assessment: **{validation_report.assessment.value}**

## Scope

This is a correctness and research-validity milestone. It does not claim that the
candidate is profitable, deployable, or robust outside the fixed HistData sample.

## Reproducibility

- Source: 36 monthly HistData XAUUSD bid/ask tick Parquets, 2015-2017
- Source ticks: {bar_summary.get('source_ticks', 'see processed manifest')}
- M15 rows: {bar_summary['rows']}
- Feature dataset SHA-256: `{feature_summary['sha256']}`
- Statistical report SHA-256: `{candidate.source_evidence_sha256}`
- Research period: 2015; validation period: 2016; final unseen test: 2017
- Candidate SHA-256: `{candidate.fingerprint()}`
- Validation plan SHA-256: `{validation_report.plan_sha256}`

## Research Finding

Event: a fully closed bullish M15 candle with body/range >= {threshold}. The predeclared
outcome was the midpoint return after {research_horizon} observed bars.

- Selected non-overlapping events: {experiment_result.manifest.selected_event_count}
- Conditional mean: {_format_percentage(horizon.event_forward_return.mean)}
- Baseline mean: {_format_percentage(horizon.baseline_forward_return.mean)}
- Excess mean: {_format_percentage(horizon.excess_mean_return)}
- 95% excess-mean CI: {horizon.excess_mean_confidence_interval}
- Adjusted q-value: {horizon.adjusted_q_value}
- Reviewed finding: `{finding.finding_id}` ({finding.status.value})

## Strategy Candidate

`{candidate.candidate_id}` enters long at the next observed ask open after the event and
exits at the bid open after {holding_bars} observed bars. Its source finding was rejected,
so this frozen rule is a **pipeline probe**, not a qualifying candidate. Position sizing
is normalized 100% notional. There is no stop loss or take profit, historical spread is
paid directly, and primary slippage is zero beyond spread. The stress case adds
{stress_slippage} bps adverse slippage per side.

## Validation Results

| Split | Trades | Mean/trade | Cumulative | Max drawdown | Stress mean/trade | Criteria passed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

Predeclared evaluation criteria require at least {minimum_trades} trades, positive mean
return after observed spread in both primary and stress executions, and maximum drawdown
no greater than {drawdown_limit}. The final assessment is mechanical application of those
frozen criteria, not a profitability optimization.

## Limitations

- One instrument, one timeframe, one historical quote source, and one three-year regime.
- Tick timestamps and quotes were validated, but no provider-specific holiday/session
  calendar is available.
- Market impact, latency, rejected fills, swaps, financing, and broker contract sizing
  are not modeled.
- Holding periods count observed bars, so a position may span a session gap.
- The bootstrap treats the unconditional baseline mean as fixed and only partially
  addresses serial dependence.
- The final-test result must not be used to revise revision 1; any change requires a new
  candidate revision and a new unseen period.
"""
    REPORT_PATH.write_text(content, encoding="utf-8")


def run_pipeline(config_path: Path) -> dict[str, object]:
    config = _load_yaml(config_path)
    code_version = source_code_fingerprint(config_path)
    _, _, bar_summary = _prepare_bars(config)
    feature_frame, feature_manifest, feature_summary = _prepare_features(
        config,
        code_version=code_version,
    )
    experiment_config = _experiment_config(config, feature_manifest=feature_manifest)
    experiment_registry = ExperimentRegistry(EXPERIMENT_REGISTRY_PATH)
    experiment_result = run_experiment(
        experiment_config,
        registry=experiment_registry,
        artifact_root=EXPERIMENT_RUN_ROOT,
        code_version=code_version,
        working_directory=PROJECT_ROOT,
    )
    report_path = experiment_result.artifact_directory / "statistical_report.json"
    summary: dict[str, object] = {
        "pipeline_id": config["pipeline_id"],
        "bars": bar_summary,
        "features": feature_summary,
        "research": {
            "run_id": experiment_result.manifest.run_id,
            "artifact_directory": _relative(experiment_result.artifact_directory),
            "statistical_report_sha256": file_sha256(report_path),
            "report": experiment_result.statistical_report.model_dump(mode="json"),
        },
    }

    review_path = _project_path(str(config["review"]))
    if not review_path.is_file():
        summary["status"] = "awaiting_human_research_review"
        summary["required_review_path"] = _relative(review_path)
        return summary

    finding, _ = _review_and_promote(
        config,
        experiment_config,
        experiment_registry,
        experiment_result.manifest.run_id,
        report_path,
    )
    candidate = _candidate(config, finding)
    plan = _validation_plan(config, candidate, feature_manifest.output_sha256)
    validation_report = run_chronological_validation(feature_frame, candidate, plan)
    artifacts = _write_validation_artifacts(
        feature_frame,
        candidate,
        plan,
        validation_report,
        code_version=code_version,
        pipeline_config_path=config_path,
    )
    _write_markdown_report(
        config,
        experiment_result,
        finding,
        candidate,
        validation_report,
        bar_summary,
        feature_summary,
    )
    summary.update(
        {
            "status": "complete",
            "finding_id": finding.finding_id,
            "candidate_id": candidate.candidate_id,
            "candidate_sha256": candidate.fingerprint(),
            "validation_assessment": validation_report.assessment.value,
            "validation_artifacts": artifacts,
            "report_path": _relative(REPORT_PATH),
        }
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    summary = run_pipeline(config_path)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
