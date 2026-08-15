"""
state/universe.py — Shared persisted symbol restriction for all trading modes.

The enabled-symbol list is the single source of truth the autonomous agent
uses to restrict its universe across backtesting, paper trading, and (future)
live trading. It lives in ``state/universe.json``:

    { "symbols": ["AAPL", "MSFT"], "updated_at": "..." }

An empty ``symbols`` list means "no restriction" — i.e. the agent trades the
full default universe (S&P 500). All modes read this on spawn and append
``--symbols`` to the subprocess command when non-empty.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from config.paths import STATE_DIR

# Default persistence path. Overridable via env for tests / flexibility.
_DEFAULT_PATH = os.environ.get("UNIVERSE_STORE_PATH", str(STATE_DIR / "universe.json"))


class UniverseStore:
    """Load/save the shared, persisted symbol restriction list."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else Path(_DEFAULT_PATH)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """Return the persisted universe doc, or the empty default if absent/corrupt."""
        if not self.path.exists():
            return _empty_doc()
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return _empty_doc()
            symbols = data.get("symbols")
            if not isinstance(symbols, list):
                return _empty_doc()
            return {
                "symbols": [str(s) for s in symbols if s],
                "updated_at": data.get("updated_at", ""),
            }
        except Exception as exc:
            logger.warning("Failed to read universe store %s: %s", self.path, exc)
            return _empty_doc()

    def symbols(self) -> list[str]:
        """Return the enabled symbol list (order-preserving); empty = unrestricted."""
        return self.load()["symbols"]

    def save(self, symbols: list[str]) -> dict[str, Any]:
        """Persist a normalized, deduped symbol list. Returns the saved doc."""
        seen: set[str] = set()
        clean: list[str] = []
        for s in symbols or []:
            up = str(s).strip().upper()
            if up and up not in seen:
                seen.add(up)
                clean.append(up)

        doc = {
            "symbols": clean,
            "updated_at": _now_iso(),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to write universe store %s: %s", self.path, exc)
        return doc


# ─── Module-level convenience (matches api/shared get_fixture_provider pattern) ───

_default_store: UniverseStore | None = None


def get_universe_store() -> UniverseStore:
    """Return the shared UniverseStore singleton (injectable in tests)."""
    global _default_store
    if _default_store is None:
        _default_store = UniverseStore()
    return _default_store


def get_restricted_symbols() -> list[str]:
    """Return the persisted enabled symbol list (empty = unrestricted)."""
    return get_universe_store().symbols()


def save_restricted_symbols(symbols: list[str]) -> dict[str, Any]:
    """Persist the enabled symbol list. Returns the saved doc."""
    return get_universe_store().save(symbols)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _empty_doc() -> dict[str, Any]:
    return {"symbols": [], "updated_at": ""}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
