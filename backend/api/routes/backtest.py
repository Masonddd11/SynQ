"""Backtest routes — /api/backtest/* (local-only)."""

import os
import sys
import threading
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.shared import (
    SESSIONS_DIR,
    BacktestRun,
    get_fixture_provider,
    procs,
    read_json,
    run_backtest_subprocess,
    run_lock,
    runs,
    tail_log,
)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


# ─── Request models ─────────────────────────────────────────────────────────


class PreconditionRequest(BaseModel):
    session_id: str
    start_date: str
    end_date: str | None = None
    sim_days: int = 20
    start_cash: float = 100_000.0
    model_id: str | None = None
    extended_thinking: bool = False
    extended_thinking_budget: int = 2048
    enable_playbook: bool = True
    run_mode: str = "local"
    symbols: list[str] | None = None
    market_cap_filter: str | None = None


class SimulationRequest(BaseModel):
    session_id: str
    snapshot_session: str
    start_date: str | None = None
    end_date: str | None = None
    sim_days: int = 20
    model_id: str | None = None
    extended_thinking: bool = False
    extended_thinking_budget: int = 2048
    enable_playbook: bool = True
    run_mode: str = "local"


# ─── Helpers ────────────────────────────────────────────────────────────────


def _compute_sim_days(start_date: str, end_date: str) -> int:
    """Count trading days between start and end using SPY fixture."""
    try:
        provider = get_fixture_provider()
        ref = "SPY" if "SPY" in provider.available_symbols else provider.available_symbols[0]
        spy_dates = provider.get_bars([ref])[ref].index.strftime("%Y-%m-%d").tolist()
        trading_days = [d for d in spy_dates if start_date <= d <= end_date]
        return max(1, len(trading_days))
    except Exception:
        from datetime import date, timedelta
        d0 = date.fromisoformat(start_date)
        d1 = date.fromisoformat(end_date)
        days = 0
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:
                days += 1
            cur += timedelta(days=1)
        return max(1, days)


# ─── Endpoints ──────────────────────────────────────────────────────────────


def _resolve(requested_source: str, requested_symbols, market_cap: str | None) -> dict:
    """Resolve a requested universe against available fixture symbols."""
    from config.settings import get_settings
    from tools.data.universe import fetch_market_caps, resolve_universe

    settings = get_settings()
    provider = get_fixture_provider()
    available = set(provider.available_symbols)

    # When a market-cap filter is active on a CUSTOM (bounded) universe, fetch
    # caps on demand so the filter works immediately; disks-cached thereafter.
    # For the full S&P 500 (unbounded) we only read the existing cache to avoid
    # thousands of live yfinance calls blocking a single request.
    caps = None
    if market_cap in ("low", "mid", "high") and requested_source == "custom":
        base = resolve_universe(
            source="custom",
            symbols=requested_symbols,
            market_cap=None,
            available=available,
            low_max=settings.market_cap_low_max,
            mid_max=settings.market_cap_mid_max,
        )
        caps = fetch_market_caps(base.symbols)

    res = resolve_universe(
        source=requested_source,
        symbols=requested_symbols,
        market_cap=market_cap,
        available=available,
        caps=caps,
        low_max=settings.market_cap_low_max,
        mid_max=settings.market_cap_mid_max,
    )

    # Default source: when no explicit source is given, S&P 500 is the default.
    if requested_source != "custom":
        requested_source = "sp500"

    return {
        "source": requested_source,
        "market_cap_filter": market_cap,
        "symbols": res.symbols,
        "count": len(res.symbols),
        "missing": res.missing,
        "unknown_cap": res.unknown_cap,
    }


@router.get("/universe")
def get_universe(source: str = "sp500", symbols: str = "", market_cap: str = ""):
    """Resolve a requested stock universe against available fixture data.

    Query params:
      source:     ``sp500`` (default) or ``custom``.
      symbols:    Comma-separated symbols (only meaningful when source=custom).
      market_cap: Optional bucket filter: ``low | mid | high``.

    Returns eligible symbols plus ``missing`` / ``unknown_cap`` reporting.
    """
    try:
        cap = market_cap or None
        req_symbols = [s for s in symbols.split(",") if s.strip()] if symbols else None
        return _resolve(source, req_symbols, cap)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/precondition")
def start_precondition(req: PreconditionRequest):
    """Launch a precondition backtest in a background process."""
    with run_lock:
        for r in runs.values():
            if r.status == "running" and r.config.get("run_mode") == "local":
                raise HTTPException(
                    409, f"Local backtest '{r.session_id}' is already running"
                )

    sim_days = req.sim_days
    if req.end_date:
        sim_days = _compute_sim_days(req.start_date, req.end_date)

    run_id = f"precond_{req.session_id}_{int(time.time())}"
    cmd = [
        sys.executable, "-m", "backtest.backtest",
        "--days", str(sim_days),
        "--start-date", req.start_date,
        "--start-cash", str(req.start_cash),
        "--session", req.session_id,
    ]
    if req.model_id:
        cmd += ["--model", req.model_id]

    # Universe restriction: explicit request symbols / a market-cap filter win;
    # otherwise fall back to the persisted shared Universe list (the common
    # restricter). Empty effective list => full universe (pre-feature behavior).
    if req.symbols or req.market_cap_filter:
        source = "custom" if req.symbols else "sp500"
        resolved = _resolve(source, req.symbols, req.market_cap_filter)
        if not resolved["symbols"]:
            raise HTTPException(
                400, "No symbols remain after applying the selected filters."
            )
        cmd += ["--symbols", ",".join(resolved["symbols"])]
    else:
        # No per-request restriction: apply the shared Universe list if non-empty.
        try:
            from state.universe import get_restricted_symbols
            shared = get_restricted_symbols()
            if shared:
                cmd += ["--symbols", ",".join(shared)]
        except Exception:
            pass

    os.environ["EXTENDED_THINKING_ENABLED"] = str(req.extended_thinking).lower()
    os.environ["EXTENDED_THINKING_BUDGET"] = str(req.extended_thinking_budget)
    os.environ["ENABLE_PLAYBOOK"] = str(req.enable_playbook).lower()

    session_path = SESSIONS_DIR / req.session_id
    session_path.mkdir(parents=True, exist_ok=True)
    log_path = session_path / "run.log"

    run = BacktestRun(
        run_id=run_id,
        mode="precondition",
        session_id=req.session_id,
        status="running",
        started_at=datetime.utcnow().isoformat() + "Z",
        config=req.model_dump(),
    )
    with run_lock:
        runs[run_id] = run

    t = threading.Thread(
        target=run_backtest_subprocess,
        args=(run_id, cmd, log_path),
        daemon=True,
    )
    t.start()

    return {"run_id": run_id, "status": "running", "session_id": req.session_id}


@router.post("/simulation")
def start_simulation(req: SimulationRequest):
    """Launch a simulation backtest from a precondition snapshot."""
    snapshot_path = SESSIONS_DIR / req.snapshot_session / "snapshot.json"
    snap_data = read_json(snapshot_path) if snapshot_path.exists() else None
    if not snap_data:
        raise HTTPException(
            404, f"Snapshot not found for session '{req.snapshot_session}'"
        )

    with run_lock:
        for r in runs.values():
            if r.status == "running" and r.config.get("run_mode") == "local":
                raise HTTPException(
                    409, f"Local backtest '{r.session_id}' is already running"
                )

    sim_days = req.sim_days
    if req.end_date:
        effective_start = req.start_date or snap_data.get("final_date", "")
        if effective_start:
            sim_days = _compute_sim_days(effective_start, req.end_date)

    run_id = f"sim_{req.session_id}_{int(time.time())}"
    cmd = [
        sys.executable, "-m", "backtest.backtest",
        "--snapshot", str(snapshot_path),
        "--days", str(sim_days),
        "--session", req.session_id,
    ]
    if req.start_date:
        cmd += ["--start-date", req.start_date]
    if req.model_id:
        cmd += ["--model", req.model_id]

    os.environ["EXTENDED_THINKING_ENABLED"] = str(req.extended_thinking).lower()
    os.environ["EXTENDED_THINKING_BUDGET"] = str(req.extended_thinking_budget)
    os.environ["ENABLE_PLAYBOOK"] = str(req.enable_playbook).lower()

    session_path = SESSIONS_DIR / req.session_id
    session_path.mkdir(parents=True, exist_ok=True)
    log_path = session_path / "run.log"

    run = BacktestRun(
        run_id=run_id,
        mode="simulation",
        session_id=req.session_id,
        status="running",
        started_at=datetime.utcnow().isoformat() + "Z",
        config=req.model_dump(),
    )
    with run_lock:
        runs[run_id] = run

    t = threading.Thread(
        target=run_backtest_subprocess,
        args=(run_id, cmd, log_path),
        daemon=True,
    )
    t.start()

    return {"run_id": run_id, "status": "running", "session_id": req.session_id}


@router.get("/runs")
def list_runs():
    """List all backtest runs (running + finished)."""
    with run_lock:
        result = []
        for r in runs.values():
            if r.status == "running":
                log_path = SESSIONS_DIR / r.session_id / "run.log"
                r.log_tail = tail_log(log_path)
            result.append(r.model_dump())
    return result


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    """Get status of a specific backtest run."""
    with run_lock:
        run = runs.get(run_id)
        if not run:
            raise HTTPException(404, f"Run '{run_id}' not found")
        if run.status == "running":
            log_path = SESSIONS_DIR / run.session_id / "run.log"
            run.log_tail = tail_log(log_path)
        return run.model_dump()


@router.post("/runs/{run_id}/stop")
def stop_run(run_id: str):
    """Stop a running backtest."""
    with run_lock:
        run = runs.get(run_id)
        if not run:
            raise HTTPException(404, f"Run '{run_id}' not found")
        if run.status != "running":
            raise HTTPException(409, f"Run '{run_id}' is not running (status: {run.status})")
        proc = procs.get(run_id)
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
            procs.pop(run_id, None)
        log_path = SESSIONS_DIR / run.session_id / "run.log"
        run.status = "stopped"
        run.finished_at = datetime.utcnow().isoformat() + "Z"
        run.log_tail = tail_log(log_path)
        run.error = "Stopped by user"

    return {"run_id": run_id, "status": "stopped"}


def _snapshot_entry(data: dict, session_id: str = "") -> dict:
    return {
        "session_id": data.get("session_id", session_id),
        "final_date": data.get("final_date", ""),
        "portfolio_value": data.get("portfolio_value", 0),
        "positions": list(data.get("positions", {}).keys()),
        "cash": data.get("cash", 0),
        "source": data.get("_source", "local"),
    }


@router.get("/snapshots")
def list_snapshots():
    """List available precondition snapshots for simulation (local)."""
    seen: set[str] = set()
    snapshots = []

    if SESSIONS_DIR.is_dir():
        for entry in sorted(SESSIONS_DIR.iterdir()):
            if not entry.is_dir():
                continue
            snap = entry / "snapshot.json"
            if not snap.exists():
                continue
            data = read_json(snap)
            data["_source"] = "local"
            sid = data.get("session_id", entry.name)
            seen.add(sid)
            snapshots.append(_snapshot_entry(data, entry.name))

    return snapshots
