from __future__ import annotations

import pytest

from aiquantlab.research.exceptions import RegistryConflictError, RegistryStateError
from aiquantlab.research.registry import (
    ExperimentConclusion,
    ExperimentRegistry,
    RunStatus,
)


def test_registry_tracks_identity_run_and_manual_conclusion(experiment_config, tmp_path) -> None:
    registry = ExperimentRegistry(tmp_path / "registry.json")

    first = registry.register(experiment_config, config_path="config/example.yaml")
    second = registry.register(experiment_config, config_path="ignored-on-idempotent-register")
    running = registry.begin_run(experiment_config, code_version="abc123")
    completed = registry.complete_run(
        running.run_id,
        frame_sha256="1" * 64,
        artifact_directory="experiments/run-1",
    )
    assessed = registry.set_conclusion(
        experiment_config.experiment_id,
        experiment_config.revision,
        conclusion=ExperimentConclusion.INCONCLUSIVE,
        notes="Synthetic data is not market evidence.",
    )

    assert first == second
    assert completed.status == RunStatus.COMPLETED
    assert assessed.conclusion == ExperimentConclusion.INCONCLUSIVE
    assert len(registry.list_experiments()) == 1


def test_registry_rejects_reused_revision_with_changed_config(experiment_config, tmp_path) -> None:
    registry = ExperimentRegistry(tmp_path / "registry.json")
    registry.register(experiment_config)
    changed = experiment_config.model_copy(update={"title": "A different experiment title"})

    with pytest.raises(RegistryConflictError, match="different configuration"):
        registry.register(changed)


def test_registry_requires_completed_run_before_research_conclusion(
    experiment_config,
    tmp_path,
) -> None:
    registry = ExperimentRegistry(tmp_path / "registry.json")
    registry.register(experiment_config)

    with pytest.raises(RegistryStateError, match="completed run"):
        registry.set_conclusion(
            experiment_config.experiment_id,
            experiment_config.revision,
            conclusion=ExperimentConclusion.SUPPORTED,
            notes="A conclusion cannot precede results.",
        )
