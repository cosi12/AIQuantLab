"""artifact 根目录解析。

Web 后端不持有配置数据库；唯一的运行期配置是"仓库根目录在哪里"。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT_ENVIRONMENT_VARIABLE = "AIQUANTLAB_ROOT"
_ROOT_MARKER = "pyproject.toml"


def _discover_repository_root() -> Path:
    """从本模块位置向上查找包含 pyproject.toml 的目录。"""

    for candidate in Path(__file__).resolve().parents:
        if (candidate / _ROOT_MARKER).is_file():
            return candidate
    # 找不到标记文件时退回到 web/backend 的上两级，避免抛异常导致服务无法启动。
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ArtifactRoots:
    """允许 Web 层读取的目录白名单。"""

    repository: Path
    processed_data: Path
    experiments: Path
    reports: Path

    @property
    def readable_roots(self) -> tuple[Path, ...]:
        return (self.processed_data, self.experiments, self.reports)

    def describe(self) -> dict[str, dict[str, object]]:
        """给 /api/health 与设置页使用的目录可用性描述。"""

        return {
            name: {"path": str(path), "exists": path.is_dir()}
            for name, path in (
                ("processed_data", self.processed_data),
                ("experiments", self.experiments),
                ("reports", self.reports),
            )
        }


def build_roots(repository_root: Path | str | None = None) -> ArtifactRoots:
    if repository_root is not None:
        root = Path(repository_root).resolve()
    elif environment_root := os.environ.get(ROOT_ENVIRONMENT_VARIABLE):
        root = Path(environment_root).expanduser().resolve()
    else:
        root = _discover_repository_root()
    return ArtifactRoots(
        repository=root,
        processed_data=root / "data" / "processed",
        experiments=root / "experiments",
        reports=root / "reports",
    )


@lru_cache(maxsize=1)
def default_roots() -> ArtifactRoots:
    return build_roots()
