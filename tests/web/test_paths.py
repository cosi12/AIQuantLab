"""路径白名单是 Web 层唯一的安全边界，必须单独测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from aiquantlab_web.artifacts.paths import (
    ensure_plain_name,
    ensure_within,
    read_json,
    relative_to_repository,
    tree_fingerprint,
)
from aiquantlab_web.errors import (
    ArtifactNotFoundError,
    ArtifactParseError,
    ArtifactPathError,
)


def test_ensure_within_accepts_path_inside_root(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    target = root / "nested" / "file.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")

    assert ensure_within([root], target) == target.resolve()


def test_ensure_within_rejects_escape_via_parent_traversal(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "secret.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ArtifactPathError):
        ensure_within([root], root / ".." / "secret.json")


def test_ensure_within_rejects_sibling_directory(tmp_path: Path) -> None:
    root = tmp_path / "allowed"
    sibling = tmp_path / "allowed_but_not_really"
    root.mkdir()
    sibling.mkdir()

    with pytest.raises(ArtifactPathError):
        ensure_within([root], sibling / "file.json")


@pytest.mark.parametrize(
    "name",
    ["", ".", "..", "../config.json", "nested/config.json", "nested\\config.json", ".hidden"],
)
def test_ensure_plain_name_rejects_path_semantics(name: str) -> None:
    with pytest.raises(ArtifactPathError):
        ensure_plain_name(name)


def test_ensure_plain_name_accepts_artifact_file_name() -> None:
    assert ensure_plain_name("statistical_report.json") == "statistical_report.json"


def test_read_json_distinguishes_missing_from_malformed(tmp_path: Path) -> None:
    with pytest.raises(ArtifactNotFoundError):
        read_json(tmp_path / "absent.json")

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not json", encoding="utf-8")
    with pytest.raises(ArtifactParseError):
        read_json(malformed)

    array = tmp_path / "array.json"
    array.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ArtifactParseError):
        read_json(array)


def test_tree_fingerprint_changes_when_content_changes(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_text("{}", encoding="utf-8")
    before = tree_fingerprint([path])

    path.write_text('{"changed": true}', encoding="utf-8")
    assert tree_fingerprint([path]) != before


def test_tree_fingerprint_ignores_missing_paths(tmp_path: Path) -> None:
    assert tree_fingerprint([tmp_path / "absent.json"]) == tree_fingerprint([])


def test_relative_to_repository_uses_forward_slashes(tmp_path: Path) -> None:
    nested = tmp_path / "data" / "processed" / "file.parquet"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"")

    assert relative_to_repository(tmp_path, nested) == "data/processed/file.parquet"
