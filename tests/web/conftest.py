"""Web 层测试的共享 fixture。

artifact 树由 synthetic_repository 构造；这里只负责把它包成 ArtifactRoots 与
TestClient。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from aiquantlab_web.app import create_app
from aiquantlab_web.settings import ArtifactRoots, build_roots
from fastapi.testclient import TestClient
from synthetic_repository import build_repository


@pytest.fixture
def artifact_repository(tmp_path: Path) -> Path:
    return build_repository(tmp_path / "repository")


@pytest.fixture
def roots(artifact_repository: Path) -> ArtifactRoots:
    return build_roots(artifact_repository)


@pytest.fixture
def client(roots: ArtifactRoots) -> Iterator[TestClient]:
    with TestClient(create_app(roots)) as test_client:
        yield test_client


@pytest.fixture
def empty_roots(tmp_path: Path) -> ArtifactRoots:
    return build_roots(tmp_path / "empty")


@pytest.fixture
def empty_client(empty_roots: ArtifactRoots) -> Iterator[TestClient]:
    """空仓库客户端：Web 层必须在没有任何 artifact 时也能启动并返回空集合。"""

    with TestClient(create_app(empty_roots)) as test_client:
        yield test_client
