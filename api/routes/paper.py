"""Paper trading routes — /api/paper/* (local-only execution)."""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.shared import (
    BASE_DIR,
    SESSIONS_DIR,
    BacktestRun,
    procs,
    read_json,
    read_settings,
    run_backtest_subprocess,
    run_lock,
    runs,
    session_dir,
    tail_log,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/paper", tags=["paper"])


# ─── Helpers ────────────────────────────────────────────────────────────────


def _env_keys() -> dict:
    """Resolve API keys for the trading subprocess.

    Dashboard-saved keys (state/settings.json) take precedence; values set
    in .env (via config.settings) are the fallback so the app works with
    either configuration source.
    """
    from config.settings import get_settings

    saved = read_settings().get("keys", {})
    s = get_settings()
    return {
        "alpaca_paper_api_key": saved.get("alpaca_paper_api_key") or s.alpaca_api_key,
        "alpaca_paper_secret_key": saved.get("alpaca_paper_secret_key") or s.alpaca_secret_key,
        "polygon_api_key": saved.get("polygon_api_key") or s.polygon_api_key,
        "alpaca_paper_account_name": saved.get("alpaca_paper_account_name", ""),
    }


def _write_paper_meta(session_id: str, meta: dict):
    """Write paper trading meta.json to disk (survives server restart)."""
    session_path = SESSIONS_DIR / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    meta_path = session_path / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _get_local_paper_status() -> dict | None:
    """Find the active local paper trading session from meta.json files."""
    with run_lock:
        for r in runs.values():
            if r.mode == "paper" and r.status == "running":
                log_path = SESSIONS_DIR / r.session_id / "run.log"
                r.log_tail = tail_log(log_path)
                return r.model_dump()

    if not SESSIONS_DIR.is_dir():
        return None
    for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = read_json(meta_path)
        except Exception:
            continue
        if not meta or meta.get("mode") != "paper" or meta.get("status") != "running":
            continue

        pid = meta.get("pid")
        if pid and not _is_pid_alive(pid):
            meta["status"] = "stopped"
            meta["stopped_at"] = datetime.utcnow().isoformat() + "Z"
            meta["stopped_reason"] = "process_exited"
            _write_paper_meta(d.name, meta)
            continue

        return {
            "run_id": None,
            "mode": "paper",
            "session_id": d.name,
            "status": "running",
            "started_at": meta.get("started_at", ""),
        }

    return None


def _check_eod_window() -> str | None:
    """Return 'EOD_SIGNAL' if current ET time is in the 16:00–08:00 window."""
    try:
        import pytz
        et = pytz.timezone("America/New_York")
        hour = datetime.now(et).hour
        if hour >= 16 or hour < 8:
            return "EOD_SIGNAL"
    except Exception:
        pass
    return None


def _get_today_executed_cycles(session_id: str) -> list[str]:
    """Return list of cycle types already executed today for a session."""
    try:
        import pytz
        et = pytz.timezone("America/New_York")
        today = datetime.now(et).strftime("%Y-%m-%d")
        from store.local import LocalStore
        cycles = LocalStore().load_cycles(session_id, today)
        return [c.get("cycle_type") for c in (cycles or []) if c.get("cycle_type")]
    except Exception as e:
        logger.warning("Failed to load today's cycles: %s", e)
        return []


def _get_running_cycle(session_id: str) -> str | None:
    """Check if a cycle is currently running by reading progress from store."""
    try:
        from store.local import LocalStore
        progress = LocalStore().load_progress(session_id)
        if progress and progress.get("phase") == "running":
            return progress.get("cycle")
    except Exception:
        pass
    return None


def _get_available_cycle(session_id: str) -> dict | None:
    """Return the cycle that can be manually triggered right now, or None."""
    import pytz
    et = pytz.timezone("America/New_York")
    now = datetime.now(et)
    hour = now.hour

    if hour < 9:
        return None

    running = _get_running_cycle(session_id)
    if running:
        return {"cycle": running, "is_running": True}

    today_cycles = _get_today_executed_cycles(session_id)

    if hour >= 16:
        return {"cycle": "EOD_SIGNAL", "is_rerun": "EOD_SIGNAL" in today_cycles}

    if "MORNING" not in today_cycles:
        return {"cycle": "MORNING", "is_rerun": False}
    else:
        return {"cycle": "INTRADAY", "is_rerun": "INTRADAY" in today_cycles}


def _find_last_paper_session(account_name: str = "") -> str | None:
    """Find the most recent stopped paper session to resume."""
    def _matches(meta: dict) -> bool:
        if meta.get("mode") != "paper" or meta.get("status") != "stopped":
            return False
        if account_name:
            return meta.get("account_name", "") == account_name
        return not meta.get("account_name")

    if not SESSIONS_DIR.is_dir():
        return None
    for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = read_json(meta_path)
        except Exception:
            continue
        if meta and _matches(meta):
            return meta.get("session_id", d.name)
    return None


# ─── Endpoints ──────────────────────────────────────────────────────────────


class PaperTradingRequest(BaseModel):
    model_id: str | None = None


@router.post("/start")
def start_paper_trading(req: PaperTradingRequest):
    """Start paper trading. Resumes the most recent stopped paper session if one exists."""
    saved_keys = _env_keys()
    account_name = saved_keys.get("alpaca_paper_account_name", "")

    prev_session = _find_last_paper_session(account_name=account_name)
    session_id = prev_session or f"paper_{int(time.time())}"
    is_resumed = prev_session is not None
    logger.info("Paper trading: %s session %s (account=%s)",
                "resuming" if is_resumed else "creating new", session_id,
                account_name or "(unnamed)")

    # ── Local: subprocess ──
    running = _get_local_paper_status()
    if running and running.get("status") == "running":
        raise HTTPException(
            409, f"Paper trading session '{running['session_id']}' is already running"
        )

    run_id = f"paper_{session_id}"

    cmd = [
        sys.executable, "-m", "main",
        "--paper",
        "--session", session_id,
    ]
    env_override = dict(os.environ)
    paper_key = saved_keys.get("alpaca_paper_api_key", "")
    paper_secret = saved_keys.get("alpaca_paper_secret_key", "")
    if paper_key:
        env_override["ALPACA_API_KEY"] = paper_key
    if paper_secret:
        env_override["ALPACA_SECRET_KEY"] = paper_secret
    env_override["ALPACA_BASE_URL"] = "https://paper-api.alpaca.markets"
    env_override["ALPACA_PAPER"] = "true"

    polygon_key = saved_keys.get("polygon_api_key", "")
    if polygon_key:
        env_override["POLYGON_API_KEY"] = polygon_key

    session_path = SESSIONS_DIR / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    log_path = session_path / "run.log"

    existing_meta = {}
    meta_path = session_path / "meta.json"
    if is_resumed and meta_path.exists():
        try:
            existing_meta = read_json(meta_path) or {}
        except Exception:
            pass

    _write_paper_meta(session_id, {
        "session_id": session_id,
        "mode": "paper",
        "status": "running",
        "started_at": existing_meta.get("started_at", datetime.utcnow().isoformat() + "Z"),
        "resumed_at": datetime.utcnow().isoformat() + "Z",
        "model_id": req.model_id or existing_meta.get("model_id"),
        "account_name": account_name,
        "pid": None,
    })

    run = BacktestRun(
        run_id=run_id,
        mode="paper",
        session_id=session_id,
        status="running",
        started_at=existing_meta.get("started_at", datetime.utcnow().isoformat() + "Z"),
        config=req.model_dump(),
    )
    with run_lock:
        runs[run_id] = run

    t = threading.Thread(
        target=run_backtest_subprocess,
        args=(run_id, cmd, log_path),
        kwargs={"env": env_override},
        daemon=True,
    )
    t.start()

    def _record_pid():
        for _ in range(10):
            with run_lock:
                proc = procs.get(run_id)
            if proc and proc.pid:
                _write_paper_meta(session_id, {
                    "session_id": session_id,
                    "mode": "paper",
                    "status": "running",
                    "started_at": run.started_at,
                    "resumed_at": datetime.utcnow().isoformat() + "Z",
                    "model_id": req.model_id,
                    "pid": proc.pid,
                })
                return
            time.sleep(0.2)

    threading.Thread(target=_record_pid, daemon=True).start()

    immediate_cycle = _check_eod_window()
    return {"run_id": run_id, "status": "running", "session_id": session_id,
            "immediate_cycle": immediate_cycle, "resumed": is_resumed}


@router.post("/stop")
def stop_paper_trading():
    """Stop the active paper trading session."""
    session_id = None
    with run_lock:
        for r in runs.values():
            if r.mode == "paper" and r.status == "running":
                proc = procs.get(r.run_id)
                if proc and proc.poll() is None:
                    proc.terminate()
                r.status = "stopped"
                r.finished_at = datetime.utcnow().isoformat() + "Z"
                session_id = r.session_id
                break

    if not session_id:
        status = _get_local_paper_status()
        if status and status.get("status") == "running":
            session_id = status["session_id"]
            pid = status.get("pid")
            if pid:
                try:
                    os.kill(pid, 15)
                except OSError:
                    pass

    if session_id:
        existing = {}
        meta_path = SESSIONS_DIR / session_id / "meta.json"
        if meta_path.exists():
            try:
                existing = read_json(meta_path) or {}
            except Exception:
                pass
        existing.update({
            "session_id": session_id,
            "mode": "paper",
            "status": "stopped",
            "stopped_at": datetime.utcnow().isoformat() + "Z",
        })
        existing.pop("pid", None)
        _write_paper_meta(session_id, existing)

    return {"status": "stopped", "session_id": session_id}


@router.get("/status")
def get_paper_status():
    """Get the currently running paper trading session, if any."""
    status = _get_local_paper_status()
    if status:
        return status
    last = _find_last_paper_session()
    return {"status": "stopped", "session_id": last}


@router.post("/sync-positions")
def sync_paper_positions():
    """Sync positions from Alpaca and update agent state."""
    status = get_paper_status()
    session_id = status.get("session_id") if status else None
    if not session_id:
        raise HTTPException(400, "No paper trading session found")

    try:
        # Inject Alpaca keys into env so portfolio_sync can use them.
        saved_keys = _env_keys()
        paper_key = saved_keys.get("alpaca_paper_api_key", "")
        paper_secret = saved_keys.get("alpaca_paper_secret_key", "")
        if paper_key:
            os.environ["ALPACA_API_KEY"] = paper_key
        if paper_secret:
            os.environ["ALPACA_SECRET_KEY"] = paper_secret
        os.environ.setdefault("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        os.environ["ALPACA_PAPER"] = "true"
        # Clear cached settings so new env vars are picked up
        from config.settings import get_settings
        get_settings.cache_clear()

        from tools.execution.portfolio_sync import sync_positions_from_alpaca

        result = sync_positions_from_alpaca()
        if result.get('error'):
            raise HTTPException(502, f"Alpaca sync failed: {result['error']}")

        from store.local import LocalStore
        store = LocalStore()
        state_data = store.load_state(session_id) or {}

        state_data['cash'] = result['cash']
        state_data['portfolio_value'] = result['portfolio_value']
        state_data['peak_value'] = max(
            state_data.get('peak_value', 0), result.get('peak_value', 0)
        )
        positions_full = result.get('positions_full', {})
        existing_positions = state_data.get('positions', {})
        merged = {}
        for sym, pos_data in positions_full.items():
            if sym in existing_positions:
                local = dict(existing_positions[sym])
                local['current_price'] = pos_data.get('current_price', local.get('current_price', 0))
                local['unrealized_pnl'] = pos_data.get('unrealized_pnl', local.get('unrealized_pnl', 0))
                local['qty'] = pos_data.get('qty', local.get('qty', 0))
                if pos_data.get('avg_entry_price', 0) > 0:
                    local['avg_entry_price'] = pos_data['avg_entry_price']
                merged[sym] = local
            else:
                merged[sym] = pos_data
        state_data['positions'] = merged

        trade_history_full = result.get('trade_history', [])
        if trade_history_full and not state_data.get('trade_history'):
            state_data['trade_history'] = trade_history_full

        store.save_state(session_id, state_data)

        return {
            "status": "ok",
            "cash": result['cash'],
            "portfolio_value": result['portfolio_value'],
            "position_count": len(positions_full),
            "positions": list(positions_full.keys()),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("sync-positions failed")
        raise HTTPException(500, str(e))


@router.get("/available-cycle")
def get_available_cycle():
    """Return the cycle that can be manually triggered right now."""
    status = get_paper_status()
    session_id = status.get("session_id") if status else None
    if not session_id or status.get("status") != "running":
        raise HTTPException(400, "No active paper trading session")
    result = _get_available_cycle(session_id)
    if not result:
        return {"cycle": None}
    return result


class TriggerCycleRequest(BaseModel):
    cycle: str


@router.post("/trigger-cycle")
def trigger_cycle(req: TriggerCycleRequest):
    """Manually trigger a specific trading cycle."""
    cycle = req.cycle
    if cycle not in ("MORNING", "INTRADAY", "EOD_SIGNAL"):
        raise HTTPException(400, f"Invalid cycle: {cycle}")

    status = get_paper_status()
    session_id = status.get("session_id") if status else None
    if not session_id or status.get("status") != "running":
        raise HTTPException(400, "No active paper trading session")

    available = _get_available_cycle(session_id)
    if not available or available.get("cycle") != cycle or available.get("is_running"):
        raise HTTPException(
            409, f"Cycle '{cycle}' is not available right now"
        )

    try:
        cmd = [sys.executable, "-m", "main", "--cycle", cycle,
               "--paper", "--session", session_id]

        env_override = dict(os.environ)
        saved_keys = _env_keys()
        paper_key = saved_keys.get("alpaca_paper_api_key", "")
        paper_secret = saved_keys.get("alpaca_paper_secret_key", "")
        if paper_key:
            env_override["ALPACA_API_KEY"] = paper_key
        if paper_secret:
            env_override["ALPACA_SECRET_KEY"] = paper_secret
        env_override["ALPACA_BASE_URL"] = "https://paper-api.alpaca.markets"
        env_override["ALPACA_PAPER"] = "true"

        session_path = SESSIONS_DIR / session_id
        log_path = session_path / "run.log"

        run_id = f"trigger_{cycle}_{int(datetime.utcnow().timestamp())}"
        t = threading.Thread(
            target=run_backtest_subprocess,
            args=(run_id, cmd, log_path),
            kwargs={"env": env_override},
            daemon=True,
        )
        t.start()
        logger.info("Triggered %s cycle locally for session %s", cycle, session_id)
    except Exception as e:
        logger.exception("Failed to trigger %s cycle: %s", cycle, e)
        raise HTTPException(500, f"Failed to trigger cycle: {e}")

    return {"status": "triggered", "cycle": cycle, "session_id": session_id,
            "is_rerun": available.get("is_rerun", False)}


@router.get("/sessions")
def list_paper_sessions():
    """List past paper trading sessions."""
    sessions = []
    if SESSIONS_DIR.is_dir():
        for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
            meta_path = d / "meta.json"
            if meta_path.exists():
                meta = read_json(meta_path)
                if meta and meta.get("mode") == "paper":
                    sessions.append(meta)
    return sessions
