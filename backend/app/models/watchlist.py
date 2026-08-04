"""Watchlist models."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.analysis import Analysis
from app.models.stock import Stock


class CreateWatchlistRequest(BaseModel):
    """Request to add a stock to watchlist."""

    ticker: str
    notes: str | None = None
    alert_threshold: float = Field(default=10.0, ge=1, le=50)


class UpdateWatchlistRequest(BaseModel):
    """Request to update watchlist item."""

    notes: str | None = None
    alert_threshold: float | None = Field(None, ge=1, le=50)


class WatchlistItem(BaseModel):
    """Watchlist item with stock metadata."""

    id: str
    ticker: str
    stock: Stock | None = None
    notes: str | None = None
    alert_threshold: float = 10.0
    last_analyzed_at: datetime | None = None
    latest_analysis: Analysis | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
