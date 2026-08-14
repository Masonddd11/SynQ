"""
api/shared.py — Shared state and helpers for the FastAPI routes.

Used across all route modules. Avoids circular imports by centralising
globals (_runs, _procs, _run_lock) and common I/O helpers here.
"""

import json
import logging
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ─── Paths ──────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "backtest" / "sessions"
STATE_DIR = BASE_DIR / "state"
FIXTURES_DIR = BASE_DIR / "backtest" / "fixtures"
SETTINGS_PATH = STATE_DIR / "settings.json"

# ─── JSON helpers ───────────────────────────────────────────────────────────


def read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── Session data helpers ───────────────────────────────────────────────────


def read_json_or_none(path: Path) -> Any | None:
    """Read JSON from a local file, returning None if the file is missing."""
    if path.exists():
        return read_json(path)
    return None


def session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def has_summary(session_id: str) -> bool:
    """Check if a completed summary exists for a session."""
    return read_json_or_none(session_dir(session_id) / "summary.json") is not None


def load_daily_stats(session_id: str) -> list[dict]:
    """Load daily stats from a session's local daily_stats directory."""
    stats_dir = session_dir(session_id) / "daily_stats"
    if not stats_dir.is_dir():
        return []
    stats = []
    for f in sorted(stats_dir.glob("*.json")):
        data = read_json(f)
        if data:
            stats.append(data)
    return stats


def partial_metrics_from_stats(daily_stats: list[dict], start_cash: float = 100_000) -> dict:
    """Compute partial summary metrics from daily_stats (for stopped/incomplete sessions)."""
    if not daily_stats:
        return {}
    start_cash = float(start_cash)
    last = daily_stats[-1]
    end_value = last.get("portfolio_value", start_cash)
    total_return = ((end_value - start_cash) / start_cash * 100) if start_cash else 0
    max_dd = max((s.get("max_drawdown_pct", 0) for s in daily_stats), default=0)

    # Sharpe ratio from daily excess returns
    sharpe = 0.0
    daily_rets = [s.get("daily_return_pct", 0) for s in daily_stats]
    spy_rets = [s.get("spy_daily_return_pct", 0) for s in daily_stats]
    if len(daily_rets) >= 5:
        excess = [d - s for d, s in zip(daily_rets, spy_rets)]
        mean_ex = sum(excess) / len(excess)
        var = sum((x - mean_ex) ** 2 for x in excess) / len(excess)
        if var > 0:
            sharpe = round(mean_ex / (var ** 0.5) * (252 ** 0.5), 2)

    # Average invested percentage
    avg_invested = 0.0
    invested_vals = []
    for s in daily_stats:
        pv = s.get("portfolio_value", 0)
        cash = s.get("cash", 0)
        if pv > 0:
            invested_vals.append((pv - cash) / pv * 100)
    if invested_vals:
        avg_invested = round(sum(invested_vals) / len(invested_vals), 1)

    return {
        "sim_days": len(daily_stats),
        "start_date": daily_stats[0].get("date", ""),
        "end_date": last.get("date", ""),
        "start_value": start_cash,
        "end_value": round(end_value, 2),
        "total_return_pct": round(total_return, 2),
        "spy_total_return_pct": last.get("spy_cumulative_return_pct", 0),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": sharpe,
        "avg_invested_pct": avg_invested,
        "final_positions": list(last.get("positions", {}).keys()),
        "final_position_count": last.get("position_count", 0),
    }


# ─── Settings helpers ───────────────────────────────────────────────────────


def read_settings() -> dict:
    if SETTINGS_PATH.exists():
        return read_json(SETTINGS_PATH)
    return {}


def write_settings(data: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ─── Fixture provider (cached) ─────────────────────────────────────────────

_fixture_provider = None


def get_fixture_provider():
    """Cached FixtureProvider for API use (daily bars only, ~42MB)."""
    global _fixture_provider
    if _fixture_provider is None:
        from providers import FixtureProvider
        _fixture_provider = FixtureProvider(hourly_file="__none__")
    return _fixture_provider


# ─── Run registry (shared across paper + backtest) ──────────────────────────


class BacktestRun(BaseModel):
    """Tracks an in-progress or completed backtest."""
    run_id: str
    mode: str  # "precondition", "simulation", "paper", "fixture_refresh"
    session_id: str
    status: str  # "running", "completed", "failed", "stopped"
    started_at: str
    finished_at: str | None = None
    log_tail: list[str] = []
    error: str | None = None
    config: dict = {}


# In-memory registry of runs
runs: dict[str, BacktestRun] = {}
procs: dict[str, subprocess.Popen] = {}  # run_id -> subprocess
run_lock = threading.Lock()


def run_status_for(session_id: str) -> str:
    """Get run status from in-memory registry, or derive from summary existence."""
    with run_lock:
        for r in runs.values():
            if r.session_id == session_id:
                return r.status
    return "completed" if has_summary(session_id) else "unknown"


def tail_log(log_path: Path, n: int = 30) -> list[str]:
    """Read last N lines from a log file."""
    if not log_path.exists():
        return []
    try:
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-n:]]
    except Exception:
        return []


def safe_log(log_path: Path, msg: str):
    """Append a message to a log file, silently ignoring errors."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(msg if msg.endswith("\n") else msg + "\n")
            lf.flush()
    except Exception:
        pass


def run_backtest_subprocess(run_id: str, cmd: list[str], log_path: Path, env: dict | None = None):
    """Execute backtest in a subprocess, update run status on completion."""
    log_fh = None
    try:
        log_fh = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR),
            env=env,
        )
        with run_lock:
            procs[run_id] = proc
        proc.wait()
        with run_lock:
            procs.pop(run_id, None)
            run = runs.get(run_id)
            if run and run.status == "running":
                run.finished_at = datetime.utcnow().isoformat() + "Z"
                run.log_tail = tail_log(log_path)
                if proc.returncode == 0:
                    run.status = "completed"
                else:
                    run.status = "failed"
                    run.error = f"Process exited with code {proc.returncode}"
    except Exception as exc:
        with run_lock:
            procs.pop(run_id, None)
            run = runs.get(run_id)
            if run:
                run.status = "failed"
                run.error = str(exc)
                run.finished_at = datetime.utcnow().isoformat() + "Z"
    finally:
        if log_fh is not None:
            log_fh.close()
