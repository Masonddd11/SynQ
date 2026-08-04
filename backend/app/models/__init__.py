"""Pydantic models for API request/response schemas."""

from app.models.base import CamelModel
from app.models.analysis import (
    Analysis,
    AnalysisStatus,
    Signal,
    CreateAnalysisRequest,
    AnalysisListResponse,
)
from app.models.watchlist import (
    WatchlistItem,
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
)
from app.models.alert import (
    Alert,
    AlertType,
    CreateAlertRequest,
    UpdateAlertRequest,
)
from app.models.user import Profile, Subscription
from app.models.stock import Stock
from app.models.common import Pagination, ErrorResponse

__all__ = [
    "CamelModel",
    "Analysis",
    "AnalysisStatus",
    "Signal",
    "CreateAnalysisRequest",
    "AnalysisListResponse",
    "WatchlistItem",
    "CreateWatchlistRequest",
    "UpdateWatchlistRequest",
    "Alert",
    "AlertType",
    "CreateAlertRequest",
    "UpdateAlertRequest",
    "Profile",
    "Subscription",
    "Stock",
    "Pagination",
    "ErrorResponse",
]
