"""User router - profile and subscription management."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.user import Profile, Subscription, SubscriptionTier

router = APIRouter()

# TODO: Replace with actual database queries via Supabase client
# For now, use mock data for testing

_mock_profile = Profile(
    id="user-123",
    email="trader@example.com",
    full_name="Demo Trader",
    subscription_tier=SubscriptionTier.FREE,
    created_at=datetime.now(timezone.utc),
)


@router.get("/profile", response_model=Profile)
async def get_profile():
    """Get user profile."""
    # TODO: Get user_id from JWT, query profiles table
    return _mock_profile


@router.patch("/profile", response_model=Profile)
async def update_profile(full_name: str | None = None):
    """Update user profile."""
    # TODO: Get user_id from JWT, update profiles table
    if full_name is not None:
        _mock_profile.full_name = full_name

    return _mock_profile


@router.get("/subscription", response_model=Subscription)
async def get_subscription():
    """Get subscription status and usage."""
    # TODO: Get user_id from JWT, query profiles table
    return Subscription(
        tier=_mock_profile.subscription_tier,
        analyses_used_today=2,
        daily_limit=5,
        resets_at=datetime.now(timezone.utc),
    )
