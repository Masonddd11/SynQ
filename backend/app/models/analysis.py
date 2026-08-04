"""Analysis models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.stock import Stock


class AnalysisStatus(str, Enum):
    """Analysis job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Signal(str, Enum):
    """Trading signal."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class CreateAnalysisRequest(BaseModel):
    """Request to create a new analysis."""

    ticker: str


class FundamentalResult(BaseModel):
    """Fundamental analysis result."""

    bull_case: str | None = None
    bear_case: str | None = None
    key_metrics: dict | None = None
    risk_score: float | None = None


class SentimentResult(BaseModel):
    """Sentiment analysis result."""

    score: float | None = None  # -100 to 100
    sources: list[str] | None = None
    key_themes: list[str] | None = None


class NewsItem(BaseModel):
    """A single news item."""

    title: str
    source: str
    url: str
    published_at: datetime | None = None
    sentiment: float | None = None  # -1 to 1


class NewsResult(BaseModel):
    """News analysis result."""

    recent_news: list[NewsItem] | None = None
    upcoming_catalysts: list[str] | None = None
    risk_events: list[str] | None = None


class AgentResult(BaseModel):
    """Layer 1: Agent analysis result."""

    fundamental: FundamentalResult | None = None
    sentiment: SentimentResult | None = None
    news: NewsResult | None = None


class GraphRAGResult(BaseModel):
    """Layer 2: Knowledge graph result."""

    entities: list[dict] | None = None
    relationships: list[dict] | None = None
    report: str | None = None


class EntrySignal(BaseModel):
    """Entry signal from indicator."""

    direction: str | None = None  # long, short, neutral
    stop_loss: float | None = None
    take_profit: list[float] | None = None


class IndicatorResult(BaseModel):
    """Layer 3: Technical indicator result."""

    momentum: dict | None = None
    volume: dict | None = None
    structure: dict | None = None
    volatility: dict | None = None
    entry_signal: EntrySignal | None = None


class Analysis(BaseModel):
    """Full analysis response."""

    id: str
    ticker: str
    stock: Stock | None = None
    status: AnalysisStatus
    agent_result: AgentResult | None = None
    graphrag_result: GraphRAGResult | None = None
    indicator_result: IndicatorResult | None = None
    confluence_score: float | None = Field(None, ge=0, le=100)
    signal: Signal | None = None
    created_at: datetime | None = None
    processing_started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class AnalysisListResponse(BaseModel):
    """Paginated list of analyses."""

    data: list[Analysis]
    pagination: dict
