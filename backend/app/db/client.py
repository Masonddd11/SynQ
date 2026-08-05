"""Supabase client factory."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a cached Supabase client built from settings."""
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("Supabase URL and key must be configured in settings")
    return create_client(settings.supabase_url, settings.supabase_key)
