from __future__ import annotations

import json

import pytest

from aiquantlab.data.storage import file_sha256
from aiquantlab.research.exceptions import ResearchContractError
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
