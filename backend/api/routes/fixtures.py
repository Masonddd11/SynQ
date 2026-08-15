"""Local-only fixture management + live state routes — /api/fixtures/*, /api/live/*.

All fixtures are stored and refreshed on the local filesystem under
backtest/fixtures/ (FIXTURES_DIR). No remote storage is involved.
"""

import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.shared import (
    BASE_DIR,
    FIXTURES_DIR,
    STATE_DIR,
    BacktestRun,
    procs,
    read_json,
    read_settings,
    run_lock,
    tail_log,
)

router = APIRouter(tags=["fixtures"])

# Fixture-specific run registry (separate from backtest runs)
_fixture_runs: dict[str, BacktestRun] = {}


# ─── Helpers ────────────────────────────────────────────────────────────────


def _get_bars_date_range(fixture_path: Path) -> dict:
    """Extract date range from a bars fixture JSON using SPY as reference."""
    if not fixture_path.exists():
        return {}
    try:
        data = read_json(fixture_path)
        ref = data.get("SPY", {})
        if not ref:
            ref = next(iter(data.values()), {})
        dates = sorted(ref.keys())
        if dates:
            return {
                "first_date": dates[0][:10],
                "last_date": dates[-1][:10],
                "bar_count": len(dates),
            }
    except Exception:
        pass
    return {}


def _fixture_status_local() -> dict:
    """Read fixture status from local filesystem."""
    files = {
        "daily_bars": FIXTURES_DIR / "yfinance" / "daily_bars.json",
        "hourly_bars": FIXTURES_DIR / "yfinance" / "hourly_bars.json",
        "earnings_dates": FIXTURES_DIR / "yfinance" / "earnings_dates.json",
        "sp500_tickers": FIXTURES_DIR / "wikipedia" / "sp500_tickers.json",
        "sp500_sectors": FIXTURES_DIR / "wikipedia" / "sp500_sectors.json",
    }
    result = {}
    for name, path in files.items():
        if path.exists():
            stat = path.stat()
            info: dict = {
                "exists": True,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
            if name in ("daily_bars", "hourly_bars"):
                info.update(_get_bars_date_range(path))
            result[name] = info
        else:
            result[name] = {"exists": False}

    news_dir = FIXTURES_DIR / "polygon" / "news"
    if news_dir.is_dir():
        news_files = sorted(news_dir.glob("day_*.json"))
        day_names = [f.stem.replace("day_", "") for f in news_files]
        total_size = sum(f.stat().st_size for f in news_files)
        latest_mtime = max((f.stat().st_mtime for f in news_files), default=0)
        result["news"] = {
            "exists": len(day_names) > 0,
            "day_count": len(day_names),
            "first_date": day_names[0] if day_names else None,
            "last_date": day_names[-1] if day_names else None,
            "size_bytes": total_size,
            "modified": datetime.fromtimestamp(latest_mtime).isoformat() if latest_mtime else None,
        }
    else:
        result["news"] = {"exists": False, "day_count": 0}

    return result


# ─── Fixture endpoints ──────────────────────────────────────────────────────


@router.get("/api/fixtures/status")
def get_fixture_status():
    """Check which local fixture files exist and their last modified time."""
    return _fixture_status_local()


class FixtureRefreshRequest(BaseModel):
    targets: list[str]
    news_start_date: str | None = None
    news_end_date: str | None = None


@router.post("/api/fixtures/refresh")
def start_fixture_refresh(req: FixtureRefreshRequest):
    """Launch fixture refresh scripts in a background process."""
    with run_lock:
        for r in _fixture_runs.values():
            if r.status == "running":
                raise HTTPException(409, "A fixture refresh is already running")

    run_id = f"fixture_{int(time.time())}"
    log_path = FIXTURES_DIR / "refresh.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmds: list[list[str]] = []
    non_news = [t for t in req.targets if t != "news"]
    if non_news:
        cmds.append([
            sys.executable, "-m", "backtest.fixtures.refresh",
            "--only", *non_news,
        ])
    if "news" in req.targets:
        news_cmd = [sys.executable, "-m", "backtest.fixtures.refresh_news"]
        if req.news_start_date:
            news_cmd += ["--start", req.news_start_date]
        if req.news_end_date:
            news_cmd += ["--end", req.news_end_date]
        cmds.append(news_cmd)

    run = BacktestRun(
        run_id=run_id,
        mode="fixture_refresh",
        session_id="fixtures",
        status="running",
        started_at=datetime.utcnow().isoformat() + "Z",
        config=req.model_dump(),
    )
    with run_lock:
        _fixture_runs[run_id] = run

    def _run_fixture_cmds():
        try:
            with open(log_path, "w", encoding="utf-8") as lf:
                for cmd in cmds:
                    lf.write(f">>> {' '.join(cmd)}\n")
                    lf.flush()
                    # Inject API keys from settings.json so refresh scripts can use them
                    saved_keys = read_settings().get("keys", {})
                    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
                    if saved_keys.get("polygon_api_key") and not env.get("POLYGON_API_KEY"):
                        env["POLYGON_API_KEY"] = saved_keys["polygon_api_key"]
                    proc = subprocess.Popen(
                        cmd, stdout=lf, stderr=subprocess.STDOUT,
                        cwd=str(BASE_DIR), env=env,
                    )
                    with run_lock:
                        procs[run_id] = proc
                    proc.wait()
                    if proc.returncode != 0:
                        with run_lock:
                            r = _fixture_runs.get(run_id)
                            if r and r.status == "running":
                                r.status = "failed"
                                r.error = f"Command failed with code {proc.returncode}"
                                r.finished_at = datetime.utcnow().isoformat() + "Z"
                                r.log_tail = tail_log(log_path)
                            procs.pop(run_id, None)
                        return
            with run_lock:
                procs.pop(run_id, None)
                r = _fixture_runs.get(run_id)
                if r and r.status == "running":
                    r.status = "completed"
                    r.finished_at = datetime.utcnow().isoformat() + "Z"
                    r.log_tail = tail_log(log_path)
        except Exception as exc:
            with run_lock:
                procs.pop(run_id, None)
                r = _fixture_runs.get(run_id)
                if r:
                    r.status = "failed"
                    r.error = str(exc)
                    r.finished_at = datetime.utcnow().isoformat() + "Z"

    t = threading.Thread(target=_run_fixture_cmds, daemon=True)
    t.start()

    return {
        "run_id": run_id,
        "status": "running",
        "storage": "local",
    }


@router.get("/api/fixtures/runs")
def list_fixture_runs():
    """List fixture refresh runs."""
    log_path = FIXTURES_DIR / "refresh.log"
    with run_lock:
        result = []
        for r in _fixture_runs.values():
            if r.status == "running":
                r.log_tail = tail_log(log_path)
            result.append(r.model_dump())
    return result


@router.post("/api/fixtures/runs/{run_id}/stop")
def stop_fixture_run(run_id: str):
    """Stop a running fixture refresh."""
    with run_lock:
        run = _fixture_runs.get(run_id)
        if not run:
            raise HTTPException(404, f"Run '{run_id}' not found")
        if run.status != "running":
            raise HTTPException(409, f"Run is not running (status: {run.status})")
        proc = procs.get(run_id)
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            procs.pop(run_id, None)
        log_path = FIXTURES_DIR / "refresh.log"
        run.status = "stopped"
        run.finished_at = datetime.utcnow().isoformat() + "Z"
        run.log_tail = tail_log(log_path)
        run.error = "Stopped by user"
    return {"run_id": run_id, "status": "stopped"}


# ─── Live state endpoints ───────────────────────────────────────────────────


@router.get("/api/live/portfolio")
def get_live_portfolio():
    """Current live portfolio state."""
    path = STATE_DIR / "portfolio.json"
    if not path.exists():
        raise HTTPException(404, "No live portfolio state")
    return read_json(path)


@router.get("/api/live/watchlist")
def get_live_watchlist():
    """Current watchlist."""
    path = STATE_DIR / "watchlist.json"
    if not path.exists():
        return []
    return read_json(path)
