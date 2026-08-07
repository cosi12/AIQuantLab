"""读取 reports/ 下的 Markdown 研究报告，使研究者无需手工打开文件。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aiquantlab_web.artifacts.cache import FingerprintCache
from aiquantlab_web.artifacts.paths import (
    ensure_within,
    read_text,
    relative_to_repository,
    tree_fingerprint,
)
from aiquantlab_web.errors import ArtifactNotFoundError
from aiquantlab_web.schemas import ReportDetail, ReportSummary
from aiquantlab_web.settings import ArtifactRoots

_TITLE_PATTERN = re.compile(r"^#\s+(?P<title>.+?)\s*$", re.MULTILINE)
_cache: FingerprintCache[tuple[ReportRecord, ...]] = FingerprintCache()


@dataclass(frozen=True)
class ReportRecord:
    report_id: str
    path: Path
    title: str


def _report_paths(roots: ArtifactRoots) -> list[Path]:
    if not roots.reports.is_dir():
        return []
    return sorted(path for path in roots.reports.glob("*.md") if path.is_file())


def _extract_title(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return path.stem
    match = _TITLE_PATTERN.search(content)
    return match.group("title") if match else path.stem


def load_records(roots: ArtifactRoots) -> tuple[ReportRecord, ...]:
    paths = _report_paths(roots)
    fingerprint = tree_fingerprint(paths)

    def build() -> tuple[ReportRecord, ...]:
        return tuple(
            ReportRecord(report_id=path.stem, path=path, title=_extract_title(path))
            for path in paths
        )

    return _cache.resolve(str(roots.reports), fingerprint, build)


def _summarize(roots: ArtifactRoots, record: ReportRecord) -> ReportSummary:
    stat = record.path.stat()
    return ReportSummary(
        report_id=record.report_id,
        title=record.title,
        file_name=record.path.name,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        path=relative_to_repository(roots.repository, record.path),
    )


def list_reports(roots: ArtifactRoots) -> list[ReportSummary]:
    summaries = [_summarize(roots, record) for record in load_records(roots)]
    return sorted(summaries, key=lambda summary: summary.modified_at, reverse=True)


def get_report(roots: ArtifactRoots, report_id: str) -> ReportDetail:
    for record in load_records(roots):
        if record.report_id != report_id:
            continue
        path = ensure_within(roots.readable_roots, record.path)
        return ReportDetail(
            **_summarize(roots, record).model_dump(),
            content=read_text(path),
        )
    raise ArtifactNotFoundError(f"报告不存在：{report_id}")
