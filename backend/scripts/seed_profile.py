"""Seed script ensuring a `profiles` row exists for DEV_USER_ID.

Idempotent: uses an upsert so re-runs are safe. Uses the service-role client
so RLS is bypassed and the write is not gated by profile ownership policies.
"""

import sys
from pathlib import Path

import supabase

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

DEFAULT_PROFILE_EMAIL = "dev@synq.local"


def _service_client() -> supabase.Client:
    """Build a service-role client (bypasses RLS)."""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured in .env")
    return supabase.create_client(settings.supabase_url, settings.supabase_service_key)


def seed_profile(dev_user_id: str | None = None, email: str = DEFAULT_PROFILE_EMAIL) -> dict | None:
    """Ensure a `profiles` row exists for ``dev_user_id``.

    Uses the id from ``settings.dev_user_id`` when ``dev_user_id`` is not passed.
    Returns the upserted row, or ``None`` if no user id is configured.
    """
    user_id = dev_user_id or settings.dev_user_id
    if not user_id:
        print("No DEV_USER_ID configured in .env; nothing to seed.")
        return None

    client = _service_client()
    profile = {
        "id": user_id,
        "email": email,
        # A missing profile breaks the analyses insert (check_analysis_limit
        # trigger reads this too), so ensure a usable tier.
        "subscription_tier": "free",
    }

    try:
        result = client.table("profiles").upsert(profile, on_conflict="id").execute()
        row = result.data[0] if result.data else result.data
        print(f"  [OK] profiles row ensured for {user_id} ({email}) tier=free")
        return row
    except Exception as e:
        print(f"  [FAIL] Failed to seed profile: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    seed_profile()
