"""User router - profile and subscription management."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from supabase_auth.types import User

from app.core.auth import get_current_user
from app.models.user import Profile, Subscription, SubscriptionTier
from app.repositories.user import UserRepository

router = APIRouter()

_user_repo: UserRepository | None = None


def _get_user_repo() -> UserRepository:
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository()
    return _user_repo


def _ensure_profile(user: User) -> Profile:
    """Return the real profile, or build a minimal one from the auth user."""
    profile = _get_user_repo().get_profile(user.id)
    if profile is not None:
        return profile
    return Profile(
        id=user.id,
        email=user.email or "",
        full_name=None,
        subscription_tier=SubscriptionTier.FREE,
    )


@router.get("/profile", response_model=Profile)
async def get_profile(user: User = Depends(get_current_user)) -> Profile:
    """Get the authenticated user's profile."""
    return _ensure_profile(user)


@router.patch("/profile", response_model=Profile)
async def update_profile(
    full_name: str | None = None,
    user: User = Depends(get_current_user),
) -> Profile:
    """Update the authenticated user's profile."""
    repo = _get_user_repo()
    profile = repo.get_profile(user.id)
    if profile is None:
        # Create a new row for the auth identity.
        return repo.update_profile(user.id, full_name)
    if full_name is not None:
        return repo.update_profile(user.id, full_name)
    return profile


@router.get("/subscription", response_model=Subscription)
async def get_subscription(user: User = Depends(get_current_user)) -> Subscription:
    """Get subscription status and usage."""
    profile = _ensure_profile(user)
    daily_limit = {
        SubscriptionTier.FREE: 5,
        SubscriptionTier.PRO: 100,
        SubscriptionTier.ELITE: 999,
    }.get(profile.subscription_tier, 5)
    return Subscription(
        tier=profile.subscription_tier,
        analyses_used_today=0,
        daily_limit=daily_limit,
        resets_at=datetime.now(UTC),
    )
