"""store/factory.py — Store instance factory.

Returns a LocalStore (JSON files under backtest/sessions/) as the only
backend; this project no longer supports a remote backend.
"""

from __future__ import annotations

import logging

from store.base import SessionStore

logger = logging.getLogger(__name__)

_instance: SessionStore | None = None


def get_store() -> SessionStore:
    """Return the singleton SessionStore instance (LocalStore)."""
    global _instance
    if _instance is not None:
        return _instance

    from store.local import LocalStore
    _instance = LocalStore()
    logger.info("Store: LocalStore (JSON files)")

    return _instance
