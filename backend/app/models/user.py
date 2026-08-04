"""User profile and subscription models."""

from datetime import datetime
from enum import Enum

from app.models.base import CamelModel


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""

    FREE = "free"
    PRO = "pro"
    ELITE = "elite"


class Profile(CamelModel):
    """User profile."""

    id: str
    email: str
    full_name: str | None = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    created_at: datetime | None = None


class Subscription(CamelModel):
    """Subscription status and usage."""

    tier: SubscriptionTier
    analyses_used_today: int
    daily_limit: int
    resets_at: datetime
