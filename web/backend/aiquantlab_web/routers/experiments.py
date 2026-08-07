"""实验浏览、统计证据与 run artifact 查看。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from aiquantlab_web.artifacts import experiments as experiment_artifacts
from aiquantlab_web.artifacts import findings as finding_artifacts
from aiquantlab_web.dependencies import Roots
from aiquantlab_web.schemas import ArtifactFile, ExperimentDetail, ExperimentSummary

router = APIRouter(tags=["experiments"])


@router.get("/experiments", response_model=list[ExperimentSummary], summary="实验列表")
def list_experiments(roots: Roots) -> list[ExperimentSummary]:
    return experiment_artifacts.list_experiments(roots)


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentDetail,
    summary="实验详情：假设、配置、统计证据与结论",
)
def read_experiment(
    experiment_id: str,
    roots: Roots,
    revision: int | None = Query(default=None, ge=1),
    run_id: str | None = None,
) -> ExperimentDetail:
    related = finding_artifacts.index_by_experiment_id(roots).get(experiment_id, [])
    return experiment_artifacts.get_experiment(
        roots,
        experiment_id,
        revision=revision,
        run_id=run_id,
        related_finding_ids=related,
    )


@router.get(
    "/experiments/{experiment_id}/runs/{run_id}/artifacts",
    response_model=list[ArtifactFile],
    summary="run artifact 清单",
)
def list_run_artifacts(
    experiment_id: str,
    run_id: str,
    roots: Roots,
    revision: int | None = Query(default=None, ge=1),
) -> list[ArtifactFile]:
    return experiment_artifacts.list_run_artifacts(
        roots, experiment_id, run_id, revision=revision
    )


@router.get(
    "/experiments/{experiment_id}/runs/{run_id}/artifacts/{artifact_name}",
    summary="单个 JSON artifact 原文",
)
def read_run_artifact(
    experiment_id: str,
    run_id: str,
    artifact_name: str,
    roots: Roots,
    revision: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    return experiment_artifacts.read_run_artifact(
        roots, experiment_id, run_id, artifact_name, revision=revision
    )
