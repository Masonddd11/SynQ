"""System routes — /api/system/* (health + log)."""

import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.routes.paper import _is_pid_alive
from api.shared import (
    BASE_DIR,
    FIXTURES_DIR,
    SESSIONS_DIR,
    read_json,
    run_lock,
    runs,
    tail_log,
)
from config.settings import get_settings

router = APIRouter(prefix="/api/system", tags=["system"])

_HEARTBEAT_MAX_AGE_SECS = 300
_DATA_MAX_AGE_DAYS = 7


# ─── Scheduler helpers ──────────────────────────────────────────────────────


def _active_paper_session() -> tuple[str, dict] | None:
    """Return (session_id, meta) of the running paper session, else None."""
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
        if meta and meta.get("mode") == "paper" and meta.get("status") == "running":
            return d.name, meta
    return None


def _check_scheduler() -> dict:
    """Report scheduler health from the active paper session's heartbeat."""
    found = _active_paper_session()
    if not found:
        return {"name": "scheduler", "status": "idle", "detail": "No active paper session"}
    session_id, meta = found
    pid = meta.get("pid")
    if not pid or not _is_pid_alive(pid):
        return {"name": "scheduler", "status": "down",
                "detail": f"Paper process not running (pid {pid})"}

    progress_path = SESSIONS_DIR / session_id / "progress.json"
    if not progress_path.exists():
        return {"name": "scheduler", "status": "degraded",
                "detail": f"Process alive (pid {pid}) but no progress heartbeat yet"}
    age_secs = time.time() - progress_path.stat().st_mtime
    if age_secs <= _HEARTBEAT_MAX_AGE_SECS:
        return {"name": "scheduler", "status": "ok",
                "detail": f"Paper process healthy (pid {pid}, heartbeat {int(age_secs)}s ago)"}
    return {"name": "scheduler", "status": "degraded",
            "detail": f"Process alive (pid {pid}) but heartbeat stale ({int(age_secs)}s ago)"}


# ─── Health checks ──────────────────────────────────────────────────────────


def _check_api() -> dict:
    return {"name": "api", "status": "ok", "detail": "API server responding"}


def _check_frontend() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:3000/", timeout=1) as resp:
            return {"name": "frontend", "status": "ok", "detail": f"HTTP {resp.status}"}
    except Exception as e:
        return {"name": "frontend", "status": "down", "detail": str(e)}


def _check_data() -> dict:
    if not FIXTURES_DIR.is_dir():
        return {"name": "data", "status": "down", "detail": "Fixtures directory missing"}
    files = [p for p in FIXTURES_DIR.rglob("*") if p.is_file()]
    if not files:
        return {"name": "data", "status": "down", "detail": "Fixtures directory empty"}
    newest = max(p.stat().st_mtime for p in files)
    newest_iso = datetime.fromtimestamp(newest).isoformat()
    age_days = (time.time() - newest) / 86400
    if age_days > _DATA_MAX_AGE_DAYS:
        return {"name": "data", "status": "degraded",
                "detail": f"{len(files)} files, newest {newest_iso} ({age_days:.1f} days old)"}
    return {"name": "data", "status": "ok", "detail": f"{len(files)} files, newest {newest_iso}"}


def _check_llm() -> dict:
    from config.settings import get_settings
    s = get_settings()
    if s.llm_base_url and s.llm_api_key:
        return {"name": "llm", "status": "ok", "detail": "LLM endpoint configured"}
    return {"name": "llm", "status": "not_configured",
            "detail": "LLM base URL / API key not set"}


def _check_broker() -> dict:
    from config.settings import get_settings
    s = get_settings()
    if s.alpaca_api_key and s.alpaca_secret_key:
        return {"name": "broker", "status": "ok", "detail": "Alpaca API / secret keys configured"}
    return {"name": "broker", "status": "not_configured",
            "detail": "Alpaca API / secret keys not set"}


def _check_store() -> dict:
    from config.settings import get_settings
    store_path = Path(get_settings().session_dir)
    if not store_path.is_absolute():
        store_path = BASE_DIR / store_path
    if not store_path.is_dir():
        return {"name": "store", "status": "down", "detail": f"Session directory missing: {store_path}"}
    probe = store_path / f".health_probe_{os.getpid()}.tmp"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as e:
        return {"name": "store", "status": "down",
                "detail": f"Session directory not writable: {e}"}
    return {"name": "store", "status": "ok", "detail": f"Session directory writable: {store_path}"}


def _check_cache() -> dict:
    from config.settings import get_settings
    cache_path = Path(get_settings().cache_dir)
    if not cache_path.is_absolute():
        cache_path = BASE_DIR / cache_path
    if cache_path.is_dir():
        return {"name": "cache", "status": "ok", "detail": f"Cache directory exists: {cache_path}"}
    return {"name": "cache", "status": "down", "detail": f"Cache directory missing: {cache_path}"}


# ─── Manual service probes (POST /api/system/check/{service}) ────────────────

_CHECK_ALLOWLIST = {"api", "frontend", "scheduler", "data", "llm", "broker", "store", "cache"}
_ALPACA_BASE_URL = "https://paper-api.alpaca.markets"


def _http_request(url, *, method="GET", timeout, headers=None, data=None):
    """Bounded HTTP helper for manual probes — returns (status, body_bytes)."""
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def _check_result(service, ok, status, detail, error=None):
    return {"service": service, "ok": ok, "status": status, "latency_ms": 0,
            "detail": detail, "error": error}


def _probe_api() -> dict:
    try:
        status, _ = _http_request("http://127.0.0.1:8000/api/system/health", timeout=2)
    except urllib.error.HTTPError as e:
        return _check_result("api", False, "down", f"Loopback returned HTTP {e.code}", str(e))
    except Exception as e:
        return _check_result("api", False, "down", "Loopback GET failed", str(e))
    if 200 <= status < 300:
        return _check_result("api", True, "ok", f"Loopback GET /api/system/health returned {status}")
    return _check_result("api", False, "down", f"Loopback GET /api/system/health returned {status}")


def _probe_frontend() -> dict:
    try:
        status, _ = _http_request("http://127.0.0.1:3000/", timeout=2)
    except urllib.error.HTTPError as e:
        return _check_result("frontend", False, "down", f"Loopback returned HTTP {e.code}", str(e))
    except Exception as e:
        return _check_result("frontend", False, "down", "Loopback GET failed", str(e))
    if 200 <= status < 300:
        return _check_result("frontend", True, "ok", f"Loopback GET / returned {status}")
    return _check_result("frontend", False, "down", f"Loopback GET / returned {status}")


def _probe_scheduler() -> dict:
    found = _active_paper_session()
    if not found:
        return _check_result("scheduler", True, "idle", "No active paper session")
    session_id, meta = found
    pid = meta.get("pid")
    if not pid:
        return _check_result("scheduler", False, "degraded",
                             "Paper session starting (pid not recorded yet)")
    try:
        alive = _is_pid_alive(pid)
    except Exception as e:
        return _check_result("scheduler", False, "down", "Failed checking paper process", str(e))
    if not alive:
        return _check_result("scheduler", False, "down", f"Paper process not running (pid {pid})")

    progress_path = SESSIONS_DIR / session_id / "progress.json"
    try:
        if not progress_path.exists():
            base = "Process alive but no progress heartbeat yet"
            ok = False
        else:
            age = time.time() - progress_path.stat().st_mtime
            if age <= _HEARTBEAT_MAX_AGE_SECS:
                base = f"Paper process healthy (pid {pid}, heartbeat {int(age)}s ago)"
                ok = True
            else:
                base = f"Process alive but heartbeat stale ({int(age)}s ago)"
                ok = False
    except Exception as e:
        return _check_result("scheduler", False, "degraded",
                             "Failed reading progress heartbeat", str(e))

    fragment = ""
    try:
        for key in ("last_cycle", "last_cycle_at"):
            val = meta.get(key)
            if val:
                fragment = f" | last cycle: {val}"
                break
        if not fragment and progress_path.exists():
            progress = read_json(progress_path)
            for key in ("phase", "cycle"):
                val = progress.get(key)
                if val:
                    fragment = f" | last cycle: {val}"
                    break
    except Exception:
        pass  # last-cycle info is best-effort only
    status = "ok" if ok else "degraded"
    return _check_result("scheduler", ok, status, base + fragment)


def _probe_data() -> dict:
    if not FIXTURES_DIR.is_dir():
        return _check_result("data", False, "down", "Fixtures directory missing")
    try:
        files = [p for p in FIXTURES_DIR.rglob("*.json") if p.is_file()]
    except Exception as e:
        return _check_result("data", False, "down", "Failed scanning fixtures", str(e))
    if not files:
        return _check_result("data", False, "down", "No fixture JSON files")
    try:
        newest = max(files, key=lambda p: p.stat().st_mtime)
        newest_mtime = newest.stat().st_mtime
    except Exception as e:
        return _check_result("data", False, "down", "Failed statting newest fixture", str(e))
    try:
        with open(newest, encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        return _check_result("data", False, "down", f"Fixture not parseable: {newest.name}", str(e))
    age_days = (time.time() - newest_mtime) / 86400
    if age_days > _DATA_MAX_AGE_DAYS:
        return _check_result("data", False, "degraded",
                             f"{newest.name} parsed but stale ({age_days:.1f}d old)")
    return _check_result("data", True, "ok", f"{newest.name} parsed ({age_days:.1f}d old)")


def _probe_llm() -> dict:
    try:
        s = get_settings()
    except Exception as e:
        return _check_result("llm", False, "down", "Failed loading settings", str(e))
    if not (s.llm_base_url and s.llm_api_key):
        return _check_result("llm", False, "not_configured",
                             "LLM not configured (missing llm_base_url or llm_api_key)")
    url = s.llm_base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": s.llm_model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }).encode()
    try:
        status, _ = _http_request(
            url, method="POST", timeout=8,
            headers={"Authorization": f"Bearer {s.llm_api_key}",
                     "Content-Type": "application/json"},
            data=body,
        )
    except urllib.error.HTTPError as e:
        return _check_result("llm", False, "down", f"LLM returned HTTP {e.code}", str(e))
    except Exception as e:
        return _check_result("llm", False, "down", "LLM request failed", str(e))
    if 200 <= status < 300:
        return _check_result("llm", True, "ok", f"LLM completion returned HTTP {status}")
    return _check_result("llm", False, "down", f"LLM returned HTTP {status}")


def _probe_broker() -> dict:
    try:
        s = get_settings()
    except Exception as e:
        return _check_result("broker", False, "down", "Failed loading settings", str(e))
    api_key = s.alpaca_api_key
    secret = s.alpaca_secret_key
    try:
        from api.shared import SETTINGS_PATH
        saved = read_json(SETTINGS_PATH).get("keys", {}) if SETTINGS_PATH.exists() else {}
        api_key = saved.get("alpaca_paper_api_key") or api_key
        secret = saved.get("alpaca_paper_secret_key") or secret
    except Exception:
        pass  # fall back to env-configured keys
    if not (api_key and secret):
        return _check_result("broker", False, "not_configured",
                             "Alpaca not configured (missing alpaca keys)")
    auth = base64.b64encode(f"{api_key}:{secret}".encode()).decode()
    try:
        status, resp_body = _http_request(
            _ALPACA_BASE_URL + "/v2/clock", timeout=8,
            headers={"Authorization": "Basic " + auth},
        )
    except urllib.error.HTTPError as e:
        return _check_result("broker", False, "down", f"Alpaca returned HTTP {e.code}", str(e))
    except Exception as e:
        return _check_result("broker", False, "down", "Alpaca request failed", str(e))
    if not (200 <= status < 300):
        return _check_result("broker", False, "down", f"Alpaca returned HTTP {status}")
    try:
        is_open = json.loads(resp_body).get("is_open")
    except Exception as e:
        return _check_result("broker", False, "down", "Alpaca clock response unparseable", str(e))
    return _check_result("broker", True, "ok",
                         f"Alpaca clock: market {'open' if is_open else 'closed'}")


def _probe_store() -> dict:
    probe = SESSIONS_DIR / f".__selftest__{int(time.time() * 1000)}.probe"
    token = secrets.token_hex(8)
    try:
        try:
            probe.write_text(token, encoding="utf-8")
            got = probe.read_text(encoding="utf-8")
        finally:
            probe.unlink(missing_ok=True)
    except Exception as e:
        return _check_result("store", False, "down", "Store round-trip failed", str(e))
    if got != token:
        return _check_result("store", False, "down", "Store round-trip mismatch")
    return _check_result("store", True, "ok", f"Session dir round-trip OK ({len(token)} bytes)")


def _probe_cache() -> dict:
    try:
        s = get_settings()
        cache_path = Path(s.cache_dir) if s.cache_dir else Path(".cache/market_data")
        if not cache_path.is_absolute():
            cache_path = BASE_DIR / cache_path
        from tools.data.cache import DataCache
        import pandas as pd
        cache = DataCache(str(cache_path))
        key = f"__selftest__{int(time.time() * 1000)}"
        df = pd.DataFrame({"a": [1]})
        try:
            cache.put(key, df)
            got = cache.get(key, max_age_hours=24)
        finally:
            cache._path(key).unlink(missing_ok=True)
    except ImportError:
        return _check_result("cache", False, "down", "pandas not available")
    except Exception as e:
        return _check_result("cache", False, "down", "Cache round-trip failed", str(e))
    if got is not None and not got.empty:
        return _check_result("cache", True, "ok", "Cache put/get round-trip OK")
    return _check_result("cache", False, "down", "Cache round-trip failed (empty or missing)")


_PROBES = {
    "api": _probe_api, "frontend": _probe_frontend, "scheduler": _probe_scheduler,
    "data": _probe_data, "llm": _probe_llm, "broker": _probe_broker,
    "store": _probe_store, "cache": _probe_cache,
}


# ─── Health aggregation ─────────────────────────────────────────────────────


def _collect_services() -> list[dict]:
    checks = [
        _check_api,
        _check_frontend,
        _check_scheduler,
        _check_data,
        _check_llm,
        _check_broker,
        _check_store,
        _check_cache,
    ]
    return [check() for check in checks]


def _overall(services: list[dict]) -> str:
    statuses = {s["status"] for s in services}
    if "down" in statuses:
        return "down"
    if statuses & {"degraded", "not_configured"}:
        return "degraded"
    return "ok"


# ─── Log helpers ────────────────────────────────────────────────────────────


def _active_session_ids() -> list[str]:
    """Session ids with a running run or a running paper meta.json."""
    ids: set[str] = set()
    with run_lock:
        for r in runs.values():
            if r.status == "running":
                ids.add(r.session_id)
    if SESSIONS_DIR.is_dir():
        for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
            meta_path = d / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = read_json(meta_path)
            except Exception:
                continue
            if meta and meta.get("mode") == "paper" and meta.get("status") == "running":
                ids.add(d.name)
    return sorted(ids)


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/health")
def get_system_health():
    """Summary health of api, frontend, scheduler, data, llm, broker, store, cache."""
    try:
        services = _collect_services()
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall": _overall(services),
            "services": services,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/log")
def get_system_log(limit: int = 50):
    """Tail run.log for each active session, plus the fixture refresh log."""
    try:
        n = max(1, min(limit, 500))
        sources: list[dict] = []
        for session_id in _active_session_ids():
            log_path = SESSIONS_DIR / session_id / "run.log"
            sources.append({
                "name": f"session:{session_id}",
                "path": str(log_path),
                "lines": tail_log(log_path, n),
            })
        refresh_log = FIXTURES_DIR / "refresh.log"
        if refresh_log.exists():
            sources.append({
                "name": "fixtures.refresh",
                "path": str(refresh_log),
                "lines": tail_log(refresh_log, n),
            })
        return {"sources": sources}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/check/{service}")
def run_service_check(service: str):
    """Run a real operation probe for one service. Unknown service -> 404."""
    if service not in _CHECK_ALLOWLIST:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")
    start = time.monotonic()
    try:
        result = _PROBES[service]()
    except Exception as e:
        result = _check_result(service, False, "down",
                               "Probe raised an unexpected error", str(e))
    result["latency_ms"] = int((time.monotonic() - start) * 1000)
    return result
