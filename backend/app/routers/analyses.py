"""Analyses router - create and query stock analyses."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.models.analysis import (
    Analysis,
    AnalysisListResponse,
    AnalysisStatus,
    CreateAnalysisRequest,
)

router = APIRouter()

# TODO: Replace with actual database queries and background task logic
# For now, use in-memory storage for testing

_analyses_db: dict[str, Analysis] = {}


async def run_analysis_job(analysis_id: str, ticker: str):
    """Background task: run the three-layer analysis."""
    # TODO: Implement actual analysis pipeline
    # 1. Update status to "processing"
    # 2. Run Layer 1: Agent analysis
    # 3. Run Layer 2: GraphRAG
    # 4. Run Layer 3: Indicator
    # 5. Calculate confluence score
    # 6. Update status to "completed"

    analysis = _analyses_db.get(analysis_id)
    if not analysis:
        return

    # Simulate processing
    analysis.status = AnalysisStatus.PROCESSING
    analysis.processing_started_at = datetime.now(timezone.utc)

    # TODO: Replace with real analysis logic
    analysis.agent_result = {
        "fundamental": {"bull_case": "Strong AI demand", "bear_case": "High valuation", "risk_score": 45},
        "sentiment": {"score": 65, "sources": ["reddit", "twitter"], "key_themes": ["AI", "growth"]},
        "news": {"recent_news": [], "upcoming_catalysts": ["Q4 earnings"], "risk_events": []},
    }
    analysis.graphrag_result = {"entities": [], "relationships": [], "report": "GraphRAG analysis pending"}
    analysis.indicator_result = {
        "momentum": {"rsi": 55, "macd": {}, "rate_of_change": 2.5},
        "volume": {"accumulation_distribution": 0.5, "volume_trend": "increasing"},
        "structure": {"trend": "uptrend", "support_levels": [120.0], "resistance_levels": [130.0]},
        "volatility": {"atr": 3.2, "regime": "normal"},
        "entry_signal": {"direction": "long", "stop_loss": 118.0, "take_profit": [128.0, 135.0, 145.0]},
    }
    analysis.confluence_score = 72.5
    analysis.signal = "buy"
    analysis.status = AnalysisStatus.COMPLETED
    analysis.completed_at = datetime.now(timezone.utc)


@router.post("", response_model=Analysis, status_code=201)
async def create_analysis(
    request: CreateAnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """Create a new stock analysis job."""
    # TODO: Validate ticker exists in stocks table
    # TODO: Check user's daily limit
    # TODO: Verify user is authenticated

    analysis_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    analysis = Analysis(
        id=analysis_id,
        ticker=request.ticker.upper(),
        status=AnalysisStatus.PENDING,
        created_at=now,
    )

    _analyses_db[analysis_id] = analysis

    # Enqueue background job
    background_tasks.add_task(run_analysis_job, analysis_id, request.ticker.upper())

    return analysis


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ticker: str | None = Query(None),
    status: AnalysisStatus | None = Query(None),
):
    """List user's analyses."""
    # TODO: Query analyses table filtered by user_id
    analyses = list(_analyses_db.values())

    if ticker:
        analyses = [a for a in analyses if a.ticker == ticker.upper()]
    if status:
        analyses = [a for a in analyses if a.status == status]

    # Sort by created_at desc
    analyses.sort(key=lambda a: a.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    total = len(analyses)
    start = (page - 1) * page_size
    end = start + page_size

    return AnalysisListResponse(
        data=analyses[start:end],
        pagination={
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    )


@router.get("/latest", response_model=Analysis)
async def get_latest_analysis(ticker: str = Query(...)):
    """Get latest analysis for a ticker."""
    # TODO: Query analyses table for latest completed analysis for ticker
    analyses = [
        a for a in _analyses_db.values()
        if a.ticker == ticker.upper() and a.status == AnalysisStatus.COMPLETED
    ]

    if not analyses:
        raise HTTPException(status_code=404, detail="No completed analysis found for this ticker")

    analyses.sort(key=lambda a: a.completed_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return analyses[0]


@router.get("/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str):
    """Get analysis by ID."""
    # TODO: Query analyses table by id, verify user owns it
    analysis = _analyses_db.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis
