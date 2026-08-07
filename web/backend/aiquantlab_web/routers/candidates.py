"""策略候选与验证报告浏览。"""

from __future__ import annotations

from fastapi import APIRouter

from aiquantlab_web.artifacts import candidates as candidate_artifacts
from aiquantlab_web.dependencies import Roots
from aiquantlab_web.schemas import CandidateDetail, CandidateSummary

router = APIRouter(tags=["candidates"])


@router.get("/candidates", response_model=list[CandidateSummary], summary="策略候选列表")
def list_candidates(roots: Roots) -> list[CandidateSummary]:
    return candidate_artifacts.list_candidates(roots)


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateDetail,
    summary="策略候选详情与验证结果",
)
def read_candidate(candidate_id: str, roots: Roots) -> CandidateDetail:
    return candidate_artifacts.get_candidate(roots, candidate_id)
