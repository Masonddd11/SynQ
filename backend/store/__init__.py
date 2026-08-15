"""store — Data access abstraction for session data (local JSON files)."""

from store.base import SessionStore
from store.local import LocalStore

__all__ = ["SessionStore", "LocalStore"]
