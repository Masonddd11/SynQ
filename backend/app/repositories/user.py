"""User repository — Supabase queries for the profiles table."""

from supabase import Client, create_client

from app.config import settings
from app.db.client import get_supabase
from app.models.user import Profile


class UserRepository:
    """Data access for the profiles table.

    Uses the service-role key client when available so server-side requests
    can read and write any user's profile row.
    """

    def __init__(self, client: Client | None = None) -> None:
        if client is not None:
            self._client = client
        elif settings.supabase_service_key:
            self._client = create_client(settings.supabase_url, settings.supabase_service_key)
        else:
            self._client = get_supabase()

    def get_profile(self, user_id: str) -> Profile | None:
        """Fetch the profile row for a user, or ``None`` if absent."""
        try:
            response = (
                self._client.table("profiles")
                .select("*")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
        except Exception:
            return None
        if response is None or not response.data:
            return None
        return Profile.model_validate(response.data)

    def update_profile(self, user_id: str, full_name: str | None) -> Profile:
        """Update (or create) the profile row for a user and return it.

        Only ``full_name`` is written so unrelated columns are left untouched.
        """
        try:
            if self.get_profile(user_id) is None:
                # No row yet: upsert a minimal one.
                payload: dict[str, str] = {"id": user_id}
                if full_name is not None:
                    payload["full_name"] = full_name
                response = (
                    self._client.table("profiles")
                    .upsert(payload, on_conflict="id")
                    .execute()
                )
            else:
                response = (
                    self._client.table("profiles")
                    .update({"full_name": full_name})
                    .eq("id", user_id)
                    .execute()
                )
            if response.data and len(response.data) > 0:
                return Profile.model_validate(response.data[0])
        except Exception:
            pass
        # Fall back to current state; do not raise for a missing/denied row.
        current = self.get_profile(user_id)
        if current is not None:
            return current
        return Profile(id=user_id, email="")
