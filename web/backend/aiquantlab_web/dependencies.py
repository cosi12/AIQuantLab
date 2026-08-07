"""FastAPI 依赖。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from aiquantlab_web.settings import ArtifactRoots


def get_roots(request: Request) -> ArtifactRoots:
    """artifact 根目录在应用创建时固定，测试可通过 create_app 注入临时目录。"""

    roots: ArtifactRoots = request.app.state.roots
    return roots


Roots = Annotated[ArtifactRoots, Depends(get_roots)]
