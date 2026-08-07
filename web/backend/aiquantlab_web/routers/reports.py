"""Markdown 研究报告浏览。"""

from __future__ import annotations

from fastapi import APIRouter

from aiquantlab_web.artifacts import reports as report_artifacts
from aiquantlab_web.dependencies import Roots
from aiquantlab_web.schemas import ReportDetail, ReportSummary

router = APIRouter(tags=["reports"])


@router.get("/reports", response_model=list[ReportSummary], summary="研究报告列表")
def list_reports(roots: Roots) -> list[ReportSummary]:
    return report_artifacts.list_reports(roots)


@router.get("/reports/{report_id}", response_model=ReportDetail, summary="报告原文")
def read_report(report_id: str, roots: Roots) -> ReportDetail:
    return report_artifacts.get_report(roots, report_id)
