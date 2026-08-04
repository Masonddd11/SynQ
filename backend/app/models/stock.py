"""Stock models."""

from datetime import datetime

from app.models.base import CamelModel


class Stock(CamelModel):
    """Stock metadata."""

    ticker: str
    company_name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: int | None = None
    exchange: str | None = None
    is_active: bool = True
    last_price: float | None = None
    last_updated_at: datetime | None = None
    created_at: datetime | None = None
