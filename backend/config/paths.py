"""
config/paths.py -- Single source of truth for backend runtime data locations.

The backend used to live at the repo root and referenced runtime data
(state/, .cache, backtest/sessions) via CWD-relative strings. Now that the
backend lives in its own ``backend/`` directory and may be launched from
several CWDs (repo root, frontend/, or inside backend/), every consumer must
anchor these paths to a single module-relative root so behaviour is identical
regardless of how the process was started.

``BASE_DIR`` is the backend package root (the directory containing ``api/``,
``main.py``, ``config/``, ``state/``, etc.).

Consumers should import from here instead of building ``Path("...")`` strings
that depend on the process working directory.
"""

from __future__ import annotations

from pathlib import Path

# Backend package root: .../backend  (parent of the config/ package).
BASE_DIR = Path(__file__).resolve().parent.parent

# Runtime data homes (all under the backend package root).
STATE_DIR = BASE_DIR / "state"
CACHE_DIR = BASE_DIR / ".cache"
SESSIONS_DIR = BASE_DIR / "backtest" / "sessions"
FIXTURES_DIR = BASE_DIR / "backtest" / "fixtures"

# Persisted application settings (written by the Settings UI).
SETTINGS_PATH = STATE_DIR / "settings.json"

# Persisted shared universe restriction list.
UNIVERSE_PATH = STATE_DIR / "universe.json"

# Log scratch dirs.
LOG_DIR = STATE_DIR / "logs"
