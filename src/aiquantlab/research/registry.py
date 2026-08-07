"""Persistent experiment identities, runs, and human-reviewed conclusions."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from aiquantlab.research.exceptions import RegistryConflictError, RegistryStateError
from aiquantlab.research.models import ExperimentConfig


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentConclusion(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    INCONCLUSIVE = "inconclusive"
    INVALID = "invalid"


class RegisteredRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    status: RunStatus
    code_version: str
    started_at: datetime
    completed_at: datetime | None = None
    frame_sha256: str | None = None
    artifact_directory: str | None = None
    error: str | None = None


class RegisteredExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str
    revision: int
    title: str
    hypothesis_statement: str
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_path: str | None = None
    registered_at: datetime
    conclusion: ExperimentConclusion = ExperimentConclusion.NOT_REVIEWED
    conclusion_notes: str | None = None
    runs: tuple[RegisteredRun, ...] = ()


class RegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    experiments: tuple[RegisteredExperiment, ...] = ()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExperimentRegistry:
    """JSON registry with atomic replacement for single-process research workflows."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _load(self) -> RegistryDocument:
        if not self.path.exists():
            return RegistryDocument()
        return RegistryDocument.model_validate_json(self.path.read_text(encoding="utf-8"))

    def _write(self, document: RegistryDocument) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(document.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def list_experiments(self) -> tuple[RegisteredExperiment, ...]:
        return self._load().experiments

    def get_experiment(self, experiment_id: str, revision: int) -> RegisteredExperiment:
        for experiment in self._load().experiments:
            if experiment.experiment_id == experiment_id and experiment.revision == revision:
                return experiment
        raise KeyError((experiment_id, revision))

    def register(
        self,
        config: ExperimentConfig,
        *,
        config_path: str | None = None,
    ) -> RegisteredExperiment:
        document = self._load()
        for experiment in document.experiments:
            if (
                experiment.experiment_id == config.experiment_id
                and experiment.revision == config.revision
            ):
                if experiment.config_sha256 != config.fingerprint():
                    raise RegistryConflictError(
                        "experiment ID and revision already use a different configuration"
                    )
                return experiment

        registered = RegisteredExperiment(
            experiment_id=config.experiment_id,
            revision=config.revision,
            title=config.title,
            hypothesis_statement=config.hypothesis.statement,
            config_sha256=config.fingerprint(),
            dataset_sha256=config.dataset.sha256,
            config_path=config_path,
            registered_at=_now(),
        )
        self._write(
            document.model_copy(update={"experiments": (*document.experiments, registered)})
        )
        return registered

    def begin_run(self, config: ExperimentConfig, *, code_version: str) -> RegisteredRun:
        if not code_version.strip():
            raise RegistryStateError("code_version must not be empty")
        document = self._load()
        experiments = list(document.experiments)
        for index, experiment in enumerate(experiments):
            if (
                experiment.experiment_id == config.experiment_id
                and experiment.revision == config.revision
            ):
                if experiment.config_sha256 != config.fingerprint():
                    raise RegistryConflictError("registered configuration fingerprint has changed")
                run = RegisteredRun(
                    run_id=uuid4().hex,
                    status=RunStatus.RUNNING,
                    code_version=code_version,
                    started_at=_now(),
                )
                experiments[index] = experiment.model_copy(
                    update={"runs": (*experiment.runs, run)}
                )
                self._write(document.model_copy(update={"experiments": tuple(experiments)}))
                return run
        raise RegistryStateError("experiment must be registered before a run begins")

    def _finish_run(
        self,
        run_id: str,
        *,
        status: RunStatus,
        frame_sha256: str | None = None,
        artifact_directory: str | None = None,
        error: str | None = None,
    ) -> RegisteredRun:
        document = self._load()
        experiments = list(document.experiments)
        for experiment_index, experiment in enumerate(experiments):
            runs = list(experiment.runs)
            for run_index, run in enumerate(runs):
                if run.run_id != run_id:
                    continue
                if run.status != RunStatus.RUNNING:
                    raise RegistryStateError("only a running experiment can be finished")
                finished = run.model_copy(
                    update={
                        "status": status,
                        "completed_at": _now(),
                        "frame_sha256": frame_sha256,
                        "artifact_directory": artifact_directory,
                        "error": error,
                    }
                )
                runs[run_index] = finished
                experiments[experiment_index] = experiment.model_copy(update={"runs": tuple(runs)})
                self._write(document.model_copy(update={"experiments": tuple(experiments)}))
                return finished
        raise KeyError(run_id)

    def complete_run(
        self,
        run_id: str,
        *,
        frame_sha256: str,
        artifact_directory: str,
    ) -> RegisteredRun:
        return self._finish_run(
            run_id,
            status=RunStatus.COMPLETED,
            frame_sha256=frame_sha256,
            artifact_directory=artifact_directory,
        )

    def fail_run(self, run_id: str, *, error: str) -> RegisteredRun:
        return self._finish_run(run_id, status=RunStatus.FAILED, error=error)

    def set_conclusion(
        self,
        experiment_id: str,
        revision: int,
        *,
        conclusion: ExperimentConclusion,
        notes: str,
    ) -> RegisteredExperiment:
        if not notes.strip():
            raise RegistryStateError("conclusion notes must explain the assessment")
        document = self._load()
        experiments = list(document.experiments)
        for index, experiment in enumerate(experiments):
            if experiment.experiment_id == experiment_id and experiment.revision == revision:
                has_completed_run = any(
                    run.status == RunStatus.COMPLETED for run in experiment.runs
                )
                if conclusion != ExperimentConclusion.INVALID and not has_completed_run:
                    raise RegistryStateError(
                        "a non-invalid conclusion requires at least one completed run"
                    )
                updated = experiment.model_copy(
                    update={"conclusion": conclusion, "conclusion_notes": notes}
                )
                experiments[index] = updated
                self._write(document.model_copy(update={"experiments": tuple(experiments)}))
                return updated
        raise KeyError((experiment_id, revision))
