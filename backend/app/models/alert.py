"""Alert models."""

from datetime import datetime
from enum import Enum

from app.models.base import CamelModel
from app.models.stock import Stock


class AlertType(str, Enum):
    """Alert type."""

    SCORE_CHANGE = "score_change"
    SIGNAL_CHANGE = "signal_change"
    PRICE_TARGET = "price_target"
    EARNINGS_WARNING = "earnings_warning"
    NEWS_SPIKE = "news_spike"


class CreateAlertRequest(CamelModel):
    """Request to create an alert."""

    ticker: str
    alert_type: AlertType
    threshold: float | None = None
    target_price: float | None = None


class UpdateAlertRequest(CamelModel):
    """Request to update an alert."""

    threshold: float | None = None
    target_price: float | None = None
    is_active: bool | None = None


class Alert(CamelModel):
    """Alert rule."""

    id: str
    ticker: str
    stock: Stock | None = None
    alert_type: AlertType
    threshold: float | None = None
    target_price: float | None = None
    is_active: bool = True
    last_triggered_at: datetime | None = None
    created_at: datetime | None = None
