from __future__ import annotations

import json

import pytest

from aiquantlab.data.models import DatasetMetadata, Timeframe
from aiquantlab.data.quality import ValidationOptions, validate_ohlcv
from aiquantlab.data.storage import file_sha256, write_processed_dataset
from aiquantlab.features import (
    default_feature_registry,
    materialize_features,
    price_structure_bundle,
)
from aiquantlab.research.exceptions import ResearchContractError
from aiquantlab.research.models import FeatureDatasetReference
from aiquantlab.research.registry import ExperimentRegistry, RunStatus
from aiquantlab.research.runner import run_experiment


def test_runner_writes_reproducible_artifacts(canonical_frame, experiment_config, tmp_path) -> None:
    dataset_path = tmp_path / "data.parquet"
    canonical_frame.to_parquet(dataset_path, index=False, engine="pyarrow")
    dataset = experiment_config.dataset.model_copy(
        update={"path": str(dataset_path), "sha256": file_sha256(dataset_path)}
    )
    config = experiment_config.model_copy(update={"dataset": dataset})
    registry = ExperimentRegistry(tmp_path / "registry.json")

    result = run_experiment(
        config,
        registry=registry,
        artifact_root=tmp_path / "artifacts",
        code_version="test-commit",
    )

    assert result.registry_run.status == RunStatus.COMPLETED
    assert result.artifact_directory.is_dir()
    assert set(result.manifest.artifact_sha256) == {
        "baseline.parquet",
        "config.resolved.json",
        "hypothesis.json",
        "observations.parquet",
        "statistical_report.json",
    }
    stored_config = json.loads(
        (result.artifact_directory / "config.resolved.json").read_text(encoding="utf-8")
    )
    assert stored_config["statistics"]["random_seed"] == 11
    assert result.manifest.config_sha256 == config.fingerprint()


def test_runner_records_checksum_failure(canonical_frame, experiment_config, tmp_path) -> None:
    dataset_path = tmp_path / "data.parquet"
    canonical_frame.to_parquet(dataset_path, index=False, engine="pyarrow")
    dataset = experiment_config.dataset.model_copy(update={"path": str(dataset_path)})
    config = experiment_config.model_copy(update={"dataset": dataset})
    registry = ExperimentRegistry(tmp_path / "registry.json")

    with pytest.raises(ResearchContractError, match="checksum"):
        run_experiment(
            config,
            registry=registry,
            artifact_root=tmp_path / "artifacts",
            code_version="test-commit",
        )

    registered = registry.get_experiment(config.experiment_id, config.revision)
    assert registered.runs[-1].status == RunStatus.FAILED
    assert "checksum" in (registered.runs[-1].error or "")


def test_runner_verifies_feature_manifest_and_applies_sample_window(
    canonical_frame,
    experiment_config,
    tmp_path,
) -> None:
    source_path = tmp_path / "source.parquet"
    feature_path = tmp_path / "features.parquet"
    source_report = validate_ohlcv(
        canonical_frame,
        ValidationOptions(timeframe=Timeframe.M15),
    )
    source_manifest = write_processed_dataset(
        canonical_frame,
        source_path,
        metadata=DatasetMetadata(
            symbol="XAUUSD",
            source="synthetic-test",
            timeframe=Timeframe.M15,
        ),
        quality_report=source_report,
    )
    materialized = materialize_features(
        source_path,
        feature_path,
        price_structure_bundle(),
        registry=default_feature_registry(),
        code_version="test-features",
    )
    sample_start = canonical_frame["timestamp"].iloc[1]
    sample_end = canonical_frame["timestamp"].iloc[6]
    dataset = experiment_config.dataset.model_copy(
        update={
            "path": str(feature_path),
            "sha256": materialized.manifest.output_sha256,
            "sample_start": sample_start,
            "sample_end": sample_end,
        }
    )
    feature_reference = FeatureDatasetReference(
        manifest_path=str(materialized.manifest_path),
        manifest_sha256=file_sha256(materialized.manifest_path),
        feature_bundle_sha256=materialized.manifest.feature_bundle_sha256,
        source_ohlcv_sha256=source_manifest.sha256,
        validity_column=materialized.manifest.validity_column,
    )
    config = experiment_config.model_copy(
        update={"dataset": dataset, "feature_dataset": feature_reference}
    )

    result = run_experiment(
        config,
        registry=ExperimentRegistry(tmp_path / "registry.json"),
        artifact_root=tmp_path / "artifacts",
        code_version="test-commit",
    )

    assert result.manifest.eligible_observation_count == 5
    assert result.manifest.feature_manifest_sha256 == feature_reference.manifest_sha256
    assert "feature_manifest.json" in result.manifest.artifact_sha256
