"""Analyses router - create and query stock analyses."""
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase_auth.types import User

from app.core.auth import get_current_user
from app.models.analysis import (
    Analysis,
    AnalysisListResponse,
    AnalysisStatus,
    CreateAnalysisRequest,
)
from app.repositories.analysis import AnalysisRepository

router = APIRouter()

_analysis_repo: AnalysisRepository | None = None


def _get_analysis_repo() -> AnalysisRepository:
    global _analysis_repo
    if _analysis_repo is None:
        _analysis_repo = AnalysisRepository()
    return _analysis_repo


@router.post("", response_model=Analysis, status_code=201)
async def create_analysis(
    request: CreateAnalysisRequest,
    user: User = Depends(get_current_user),
):
    ticker = request.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=422, detail="Ticker cannot be empty")
    return _get_analysis_repo().create_analysis(user.id, ticker)


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ticker: str | None = Query(None),
    status: AnalysisStatus | None = Query(None),
    user: User = Depends(get_current_user),
):
    data, total = _get_analysis_repo().list_analyses(
        user_id=user.id, ticker=ticker, status=status, page=page, page_size=page_size
    )
    return AnalysisListResponse(
        data=data,
        pagination={
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    )


@router.get("/latest", response_model=Analysis)
async def get_latest_analysis(
    ticker: str = Query(...),
    user: User = Depends(get_current_user),
):
    analysis = _get_analysis_repo().get_latest_analysis(user.id, ticker.upper())
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found for this ticker")
    return analysis


@router.get("/{analysis_id}", response_model=Analysis)
async def get_analysis(
    analysis_id: str,
    user: User = Depends(get_current_user),
):
    analysis = _get_analysis_repo().get_analysis(user.id, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis
