"""研究发现浏览。被拒绝的 finding 同样可见。"""

from __future__ import annotations

from fastapi import APIRouter

from aiquantlab_web.artifacts import candidates as candidate_artifacts
from aiquantlab_web.artifacts import findings as finding_artifacts
from aiquantlab_web.dependencies import Roots
from aiquantlab_web.schemas import FindingDetail, FindingSummary

router = APIRouter(tags=["findings"])


@router.get("/findings", response_model=list[FindingSummary], summary="研究发现列表")
def list_findings(roots: Roots) -> list[FindingSummary]:
    return finding_artifacts.list_findings(roots)


@router.get("/findings/{finding_id}", response_model=FindingDetail, summary="研究发现详情")
def read_finding(finding_id: str, roots: Roots) -> FindingDetail:
    derived = candidate_artifacts.index_by_finding_id(roots).get(finding_id, [])
    return finding_artifacts.get_finding(roots, finding_id, derived_candidate_ids=derived)
