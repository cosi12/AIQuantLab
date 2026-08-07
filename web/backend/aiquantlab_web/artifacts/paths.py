"""路径白名单、JSON 读取与目录指纹。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from aiquantlab_web.errors import (
    ArtifactNotFoundError,
    ArtifactParseError,
    ArtifactPathError,
)

_SHA256_BLOCK_SIZE = 1024 * 1024


def ensure_within(roots: Iterable[Path], candidate: Path) -> Path:
    """确认 candidate 位于任一允许根目录之内，返回解析后的绝对路径。"""

    resolved = candidate.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            continue
        return resolved
    raise ArtifactPathError(f"路径越出允许的 artifact 根目录：{candidate}")


def ensure_plain_name(name: str) -> str:
    """拒绝任何带路径语义的名称参数。"""

    if not name or name in {".", ".."}:
        raise ArtifactPathError("名称不能为空或指向上级目录")
    if "/" in name or "\\" in name or name.startswith("."):
        raise ArtifactPathError(f"名称不允许包含路径分隔符或以点开头：{name}")
    return name


def read_json(path: Path) -> dict[str, Any]:
    """读取 JSON 对象。缺失与格式错误分别抛出不同的领域异常。"""

    if not path.is_file():
        raise ArtifactNotFoundError(f"artifact 不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ArtifactParseError(f"artifact 不是合法 JSON：{path}（{error}）") from error
    if not isinstance(payload, dict):
        raise ArtifactParseError(f"artifact 顶层必须是 JSON 对象：{path}")
    return payload


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ArtifactNotFoundError(f"artifact 不存在：{path}")
    return path.read_text(encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_SHA256_BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_fingerprint(paths: Iterable[Path]) -> str:
    """用 mtime 与 size 构造缓存键，避免为列表请求计算内容哈希。"""

    digest = hashlib.sha256()
    for path in sorted(paths):
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(str(path).encode("utf-8"))
        digest.update(f"{stat.st_mtime_ns}:{stat.st_size}".encode())
    return digest.hexdigest()


def relative_to_repository(repository_root: Path, path: Path) -> str:
    """展示用的仓库相对路径，始终使用正斜杠。"""

    try:
        return path.resolve().relative_to(repository_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
