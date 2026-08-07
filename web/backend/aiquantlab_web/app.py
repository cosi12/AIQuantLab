"""FastAPI 应用工厂。

只暴露 GET 端点。这是架构约束而不是暂缺功能：Web 层不得写入 artifact。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aiquantlab_web import __version__
from aiquantlab_web.errors import (
    ArtifactNotFoundError,
    ArtifactParseError,
    ArtifactPathError,
)
from aiquantlab_web.routers import candidates, datasets, experiments, findings, reports, system
from aiquantlab_web.settings import ArtifactRoots, build_roots, default_roots

API_PREFIX = "/api"

# 开发期前端由 Vite 提供服务；生产部署应由同源反向代理托管静态资源。
_DEVELOPMENT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def create_app(
    roots: ArtifactRoots | None = None,
    *,
    repository_root: Path | str | None = None,
) -> FastAPI:
    application = FastAPI(
        title="AIQuantLab Research API",
        version=__version__,
        summary="AIQuantLab artifact 的只读研究接口",
        description=(
            "对 AIQuantLab artifact 层的只读视图。所有内容来自 data/processed、"
            "experiments 与 reports 目录，不存在写入端点。"
        ),
    )
    if roots is not None:
        application.state.roots = roots
    elif repository_root is not None:
        application.state.roots = build_roots(repository_root)
    else:
        application.state.roots = default_roots()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(_DEVELOPMENT_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    for router in (
        system.router,
        datasets.router,
        experiments.router,
        findings.router,
        candidates.router,
        reports.router,
    ):
        application.include_router(router, prefix=API_PREFIX)

    @application.exception_handler(ArtifactNotFoundError)
    def handle_not_found(_: Request, error: ArtifactNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.exception_handler(ArtifactPathError)
    def handle_path_error(_: Request, error: ArtifactPathError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @application.exception_handler(ArtifactParseError)
    def handle_parse_error(_: Request, error: ArtifactParseError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    return application


app = create_app()
