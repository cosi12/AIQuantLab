"""数据集浏览、质量报告与按需完整性校验。"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from aiquantlab_web.artifacts import datasets as dataset_artifacts
from aiquantlab_web.artifacts import experiments as experiment_artifacts
from aiquantlab_web.dependencies import Roots
from aiquantlab_web.schemas import (
    DatasetDetail,
    DatasetIntegrity,
    DatasetPreview,
    DatasetSummary,
    QualityReportEntry,
)

router = APIRouter(tags=["datasets"])


@router.get("/datasets", response_model=list[DatasetSummary], summary="数据集列表")
def list_datasets(roots: Roots) -> list[DatasetSummary]:
    return dataset_artifacts.list_datasets(roots)


@router.get(
    "/quality-reports",
    response_model=list[QualityReportEntry],
    summary="全部数据集质量报告",
)
def list_quality_reports(roots: Roots) -> list[QualityReportEntry]:
    return dataset_artifacts.quality_reports(roots)


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail, summary="数据集详情")
def read_dataset(dataset_id: str, roots: Roots) -> DatasetDetail:
    detail = dataset_artifacts.get_dataset(roots, dataset_id)
    experiment_index = experiment_artifacts.index_by_dataset_sha256(roots)
    used_by = experiment_index.get(detail.sha256 or "", [])
    return detail.model_copy(update={"used_by_experiments": used_by})


@router.get(
    "/datasets/{dataset_id}/integrity",
    response_model=DatasetIntegrity,
    summary="按需 SHA-256 校验（慢操作）",
)
def verify_dataset(dataset_id: str, roots: Roots) -> DatasetIntegrity:
    return dataset_artifacts.verify_integrity(roots, dataset_id)


@router.get(
    "/datasets/{dataset_id}/preview",
    response_model=DatasetPreview,
    summary="K 线预览",
)
def preview_dataset(
    dataset_id: str,
    roots: Roots,
    position: Literal["head", "tail"] = "head",
    limit: int = Query(default=20, ge=1, le=500),
) -> DatasetPreview:
    return dataset_artifacts.preview(roots, dataset_id, position=position, limit=limit)
