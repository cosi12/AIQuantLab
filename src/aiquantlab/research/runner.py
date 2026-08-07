"""End-to-end experiment execution and immutable artifact creation."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from aiquantlab.data.quality import ValidationOptions, validate_ohlcv
from aiquantlab.data.storage import file_sha256
from aiquantlab.features.models import FeatureManifest
from aiquantlab.research.event_study import EventStudyResult, run_event_study
from aiquantlab.research.exceptions import ResearchContractError
from aiquantlab.research.models import ExperimentConfig, StatisticalReport
from aiquantlab.research.registry import ExperimentRegistry, RegisteredRun
from aiquantlab.research.statistics import build_statistical_report


class ExperimentArtifactManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    run_id: str
    experiment_id: str
    revision: int
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frame_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    code_version: str
    raw_event_count: int
    selected_event_count: int
    eligible_observation_count: int
    artifact_sha256: dict[str, str]
    feature_manifest_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ExperimentRunResult:
    event_study: EventStudyResult
    statistical_report: StatisticalReport
    manifest: ExperimentArtifactManifest
    registry_run: RegisteredRun
    artifact_directory: Path


def _resolve_dataset_path(config: ExperimentConfig, working_directory: Path) -> Path:
    path = Path(config.dataset.path)
    return path if path.is_absolute() else working_directory / path


def _load_verified_frame(
    config: ExperimentConfig,
    *,
    working_directory: Path,
) -> pd.DataFrame:
    dataset_path = _resolve_dataset_path(config, working_directory)
    if not dataset_path.is_file():
        raise FileNotFoundError(dataset_path)
    actual_sha256 = file_sha256(dataset_path)
    if actual_sha256 != config.dataset.sha256:
        raise ResearchContractError("dataset checksum does not match experiment configuration")
    if dataset_path.suffix.lower() != ".parquet":
        raise ResearchContractError("automatic experiment loading currently requires Parquet")
    frame = pd.read_parquet(dataset_path, engine="pyarrow")
    quality_report = validate_ohlcv(
        frame,
        ValidationOptions(timeframe=config.dataset.timeframe),
    )
    if not quality_report.passed:
        error_codes = sorted(
            issue.code for issue in quality_report.issues if issue.severity.value == "error"
        )
        raise ResearchContractError(
            f"experiment dataset failed OHLCV validation: {error_codes}"
        )
    if config.feature_dataset is not None:
        manifest_path = Path(config.feature_dataset.manifest_path)
        if not manifest_path.is_absolute():
            manifest_path = working_directory / manifest_path
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        if file_sha256(manifest_path) != config.feature_dataset.manifest_sha256:
            raise ResearchContractError("feature manifest checksum does not match configuration")
        manifest = FeatureManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        reference = config.feature_dataset
        if manifest.output_sha256 != config.dataset.sha256:
            raise ResearchContractError("feature manifest does not identify the experiment dataset")
        if manifest.feature_bundle_sha256 != reference.feature_bundle_sha256:
            raise ResearchContractError("feature bundle checksum does not match configuration")
        if manifest.source_ohlcv_sha256 != reference.source_ohlcv_sha256:
            raise ResearchContractError("feature source checksum does not match configuration")
        if manifest.validity_column != reference.validity_column:
            raise ResearchContractError("feature validity column does not match configuration")
        if reference.validity_column not in frame:
            raise ResearchContractError("feature validity column is missing from dataset")
        frame = frame.loc[frame[reference.validity_column].fillna(False).astype(bool)]

    if config.dataset.sample_start is not None and config.dataset.sample_end is not None:
        start = pd.Timestamp(config.dataset.sample_start).tz_convert("UTC")
        end = pd.Timestamp(config.dataset.sample_end).tz_convert("UTC")
        frame = frame.loc[(frame["timestamp"] >= start) & (frame["timestamp"] < end)]
        if frame.empty:
            raise ResearchContractError("experiment sample window contains no observations")
        frame = frame.reset_index(drop=True)
    return frame


def run_experiment(
    config: ExperimentConfig,
    *,
    registry: ExperimentRegistry,
    artifact_root: str | Path,
    code_version: str,
    working_directory: str | Path | None = None,
) -> ExperimentRunResult:
    """Execute a registered event study and atomically publish its artifacts."""

    base_directory = Path.cwd() if working_directory is None else Path(working_directory)
    registry.register(config)
    started_run = registry.begin_run(config, code_version=code_version)
    root = Path(artifact_root)
    final_directory = (
        root
        / config.experiment_id
        / f"revision-{config.revision}"
        / started_run.run_id
    )
    temporary_directory = root / f".tmp-{started_run.run_id}"

    try:
        research_frame = _load_verified_frame(
            config,
            working_directory=base_directory,
        )
        event_result = run_event_study(research_frame, config.event_study)
        report = build_statistical_report(event_result, config)
        temporary_directory.mkdir(parents=True, exist_ok=False)

        config_path = temporary_directory / "config.resolved.json"
        hypothesis_path = temporary_directory / "hypothesis.json"
        observations_path = temporary_directory / "observations.parquet"
        baseline_path = temporary_directory / "baseline.parquet"
        report_path = temporary_directory / "statistical_report.json"
        config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        hypothesis_path.write_text(
            config.hypothesis.model_dump_json(indent=2), encoding="utf-8"
        )
        event_result.observations.to_parquet(observations_path, index=False, engine="pyarrow")
        event_result.baseline.to_parquet(baseline_path, index=False, engine="pyarrow")
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        feature_manifest_path: Path | None = None
        if config.feature_dataset is not None:
            configured_manifest = Path(config.feature_dataset.manifest_path)
            if not configured_manifest.is_absolute():
                configured_manifest = base_directory / configured_manifest
            feature_manifest_path = temporary_directory / "feature_manifest.json"
            shutil.copyfile(configured_manifest, feature_manifest_path)

        artifact_paths = [
            config_path,
            hypothesis_path,
            observations_path,
            baseline_path,
            report_path,
        ]
        if feature_manifest_path is not None:
            artifact_paths.append(feature_manifest_path)
        artifacts = {
            path.name: file_sha256(path)
            for path in artifact_paths
        }
        manifest = ExperimentArtifactManifest(
            run_id=started_run.run_id,
            experiment_id=config.experiment_id,
            revision=config.revision,
            config_sha256=config.fingerprint(),
            dataset_sha256=config.dataset.sha256,
            frame_sha256=event_result.frame_sha256,
            code_version=code_version,
            raw_event_count=event_result.raw_event_count,
            selected_event_count=event_result.selected_event_count,
            eligible_observation_count=event_result.eligible_observation_count,
            artifact_sha256=artifacts,
            feature_manifest_sha256=(
                config.feature_dataset.manifest_sha256
                if config.feature_dataset is not None
                else None
            ),
            created_at=datetime.now(UTC),
        )
        (temporary_directory / "run_manifest.json").write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        final_directory.parent.mkdir(parents=True, exist_ok=True)
        temporary_directory.replace(final_directory)
        completed_run = registry.complete_run(
            started_run.run_id,
            frame_sha256=event_result.frame_sha256,
            artifact_directory=str(final_directory),
        )
        return ExperimentRunResult(
            event_study=event_result,
            statistical_report=report,
            manifest=manifest,
            registry_run=completed_run,
            artifact_directory=final_directory,
        )
    except Exception as exc:
        if temporary_directory.exists():
            shutil.rmtree(temporary_directory)
        registry.fail_run(started_run.run_id, error=f"{type(exc).__name__}: {exc}")
        raise
