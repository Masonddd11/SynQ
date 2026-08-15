"""
tests/test_paper_routes.py — Contract tests for /api/paper universe wiring.

Covers: start with explicit symbols appends --symbols; no symbols falls back to
the shared Universe list; empty list => no restriction; resume reapplies
persisted symbols; GET /api/paper/universe returns the checklist.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.server import app
from state.universe import UniverseStore

client = TestClient(app)

FAKE_SP500 = ["AAPL", "MSFT", "GOOGL", "SPY"]


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Point the shared universe store at a tmp file + stub the S&P source."""
    store = UniverseStore(tmp_path / "universe.json")
    monkeypatch.setattr("state.universe.get_universe_store", lambda: store)
    monkeypatch.setattr(
        "tools.data.screener.get_sp500_tickers", lambda: list(FAKE_SP500)
    )
    yield store


class FakeThread:
    """Capture spawned thread targets/args instead of actually launching."""

    captured: list[tuple] = []

    def __init__(self, target, args=(), **kwargs):
        FakeThread.captured.append((target, args))

    def start(self):
        pass


@pytest.fixture(autouse=True)
def _fake_thread(monkeypatch):
    FakeThread.captured = []
    monkeypatch.setattr("api.routes.paper.threading.Thread", FakeThread)
    return FakeThread


def _cmd() -> list[str]:
    """Return the subprocess cmd (the thread whose args look like a command)."""
    for target, args in FakeThread.captured:
        if isinstance(args, tuple) and len(args) == 3 and isinstance(args[1], list):
            return args[1]
    raise AssertionError("No subprocess thread captured")


@pytest.fixture(autouse=True)
def _sessions_dir(tmp_path, monkeypatch):
    import api.routes.paper as paper_mod
    monkeypatch.setattr(paper_mod, "SESSIONS_DIR", tmp_path / "sessions")
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def _clean_run_registry():
    """Clear the shared in-memory run registry between tests to avoid 409s."""
    from api import shared

    with shared.run_lock:
        shared.runs.clear()
        shared.procs.clear()
    yield
    with shared.run_lock:
        shared.runs.clear()
        shared.procs.clear()


def test_start_with_explicit_symbols_appends_symbols():
    resp = client.post("/api/paper/start", json={"symbols": ["AAPL", "MSFT"]})
    assert resp.status_code == 200
    cmd = _cmd()
    assert "--symbols" in cmd
    idx = cmd.index("--symbols")
    assert "AAPL" in cmd[idx + 1]
    assert "MSFT" in cmd[idx + 1]


def test_start_empty_symbols_means_no_restriction():
    resp = client.post("/api/paper/start", json={"symbols": []})
    assert resp.status_code == 200
    assert "--symbols" not in _cmd()


def test_start_no_symbols_uses_shared_universe(_isolate):
    """Explicit request without symbols falls back to the shared Universe list."""
    _isolate.save(["AAPL", "MSFT", "IREN"])
    resp = client.post("/api/paper/start", json={})
    assert resp.status_code == 200
    cmd = _cmd()
    assert "--symbols" in cmd
    idx = cmd.index("--symbols")
    assert "AAPL" in cmd[idx + 1]
    assert "IREN" in cmd[idx + 1]


def test_start_no_symbols_and_empty_shared_universe_is_unrestricted(_isolate):
    _isolate.save([])
    resp = client.post("/api/paper/start", json={})
    assert resp.status_code == 200
    assert "--symbols" not in _cmd()


def test_start_resume_reapplies_persisted_symbols(_isolate, tmp_path):
    """Resume reuses previously saved symbols from the session meta.json."""
    # Start a session with symbols the first time.
    resp = client.post("/api/paper/start", json={"symbols": ["AAPL", "MSFT"]})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Clear the shared universe so only meta.json carries the saved symbols.
    _isolate.save([])

    # Mark the previous session as stopped so it becomes the resume candidate.
    import api.routes.paper as paper_mod
    from api.shared import read_json
    import json as _json

    meta_path = paper_mod.SESSIONS_DIR / session_id / "meta.json"
    meta = read_json(meta_path)
    meta["status"] = "stopped"
    meta_path.write_text(_json.dumps(meta), encoding="utf-8")

    # Clear the in-memory run registry so the first (faked) start is no longer
    # "running" — otherwise the second start returns a 409 Conflict.
    from api import shared
    with shared.run_lock:
        shared.runs.clear()
        shared.procs.clear()

    resp2 = client.post("/api/paper/start", json={})
    assert resp2.status_code == 200
    cmd = _cmd()
    assert "--symbols" in cmd
    idx = cmd.index("--symbols")
    assert "AAPL" in cmd[idx + 1]
    assert "MSFT" in cmd[idx + 1]


def test_paper_universe_endpoint_returns_checklist():
    resp = client.get("/api/paper/universe")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbols"] == FAKE_SP500
    assert body["count"] == len(FAKE_SP500)
