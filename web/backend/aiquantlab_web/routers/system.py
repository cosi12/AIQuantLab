"""健康检查与研究系统总览。"""

from __future__ import annotations

from fastapi import APIRouter

from aiquantlab_web import __version__
from aiquantlab_web.artifacts import overview as overview_artifacts
from aiquantlab_web.dependencies import Roots
from aiquantlab_web.schemas import Health, Overview

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health, summary="服务与 artifact 根目录可用性")
def read_health(roots: Roots) -> Health:
    return Health(
        status="ok",
        version=__version__,
        repository_root=str(roots.repository),
        roots=roots.describe(),
    )


@router.get("/overview", response_model=Overview, summary="研究系统总览")
def read_overview(roots: Roots) -> Overview:
    return overview_artifacts.build_overview(roots)
