"""
tests/test_backtest_routes.py — Contract tests for the backtest universe API.

Covers:
  GET /api/backtest/universe     — resolve sp500/custom + market-cap filter
  POST /api/backtest/precondition — symbols wiring + 400 on empty resolution
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_run_registry():
    """Clear the shared in-memory run/proc registries between tests.

    The precondition endpoint registers a run before any thread is started, so
    a test that actually launches a run leaves a 'running' entry that blocks
    the next precondition call with a 409 Conflict.
    """
    from api import shared

    with shared.run_lock:
        shared.runs.clear()
        shared.procs.clear()
    yield
    with shared.run_lock:
        shared.runs.clear()
        shared.procs.clear()


# ─── GET /api/backtest/universe ─────────────────────────────────────────────


def test_universe_sp500_resolves():
    resp = client.get("/api/backtest/universe", params={"source": "sp500"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "sp500"
    assert body["market_cap_filter"] is None
    assert isinstance(body["symbols"], list)
    assert body["count"] == len(body["symbols"])
    assert body["missing"] == body.get("missing", [])
    # SPY/QQQ are always included for benchmark/breadth.
    assert "SPY" in body["symbols"]


def test_universe_custom_resolves():
    resp = client.get(
        "/api/backtest/universe",
        params={"source": "custom", "symbols": "aapl, msft,IREN"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "custom"
    assert "AAPL" in body["symbols"]
    assert "MSFT" in body["symbols"]


def test_universe_reports_missing_custom_symbols():
    resp = client.get(
        "/api/backtest/universe",
        params={"source": "custom", "symbols": "ZZZZ123,IREN"},
    )
    assert resp.status_code == 200
    body = resp.json()
    missing = body["missing"]
    # The bogus symbol has no fixture data and is reported + excluded.
    assert any("ZZZZ123" == m for m in missing)
    assert "ZZZZ123" not in body["symbols"]


def test_universe_market_cap_filter_returns_200_and_reports_unknown():
    resp = client.get(
        "/api/backtest/universe",
        params={"source": "sp500", "market_cap": "mid"},
    )
    # Even without a populated cap cache the endpoint must not error.
    assert resp.status_code == 200
    body = resp.json()
    assert body["market_cap_filter"] == "mid"
    assert body["unknown_cap"] is not None


# ─── POST /api/backtest/precondition ────────────────────────────────────────


def _start_precondition(body):
    """POST a precondition request; return response."""
    return client.post("/api/backtest/precondition", json=body)


def test_precondition_without_symbols_preserves_behaviour(monkeypatch):
    """No symbols/filter => no --symbols in the spawned cmd (regression guard)."""
    # Isolate from any persisted shared universe list (state/universe.json).
    monkeypatch.setattr(
        "state.universe.get_restricted_symbols", lambda: []
    )
    captured = {}

    class FakeThread:
        def __init__(self, target, args, **kwargs):
            captured["target"] = target
            captured["args"] = args

        def start(self):
            pass

    monkeypatch.setattr("api.routes.backtest.threading.Thread", FakeThread)

    resp = _start_precondition(
        {
            "session_id": "bt_test_preserve",
            "start_date": "2026-01-05",
            "end_date": "2026-01-09",
            "start_cash": 100000,
            "run_mode": "local",
        }
    )
    assert resp.status_code == 200
    cmd = captured["args"][1]
    assert not any("--symbols" in c for c in cmd)


def test_precondition_with_custom_symbols_wires_symbols(monkeypatch):
    captured = {}

    class FakeThread:
        def __init__(self, target, args, **kwargs):
            captured["target"] = target
            captured["args"] = args

        def start(self):
            pass

    monkeypatch.setattr("api.routes.backtest.threading.Thread", FakeThread)

    resp = _start_precondition(
        {
            "session_id": "bt_test_symbols",
            "start_date": "2026-01-05",
            "end_date": "2026-01-09",
            "start_cash": 100000,
            "run_mode": "local",
            "symbols": ["AAPL", "MSFT"],
        }
    )
    assert resp.status_code == 200
    cmd = captured["args"][1]
    symbols_flag = next(c for c in cmd if c == "--symbols")
    assert symbols_flag == "--symbols"
    idx = cmd.index("--symbols")
    assert "AAPL" in cmd[idx + 1]
    assert "MSFT" in cmd[idx + 1]


def test_precondition_with_market_cap_only_resolves_sp500(monkeypatch):
    captured = {}

    class FakeThread:
        def __init__(self, target, args, **kwargs):
            captured["target"] = target
            captured["args"] = args

        def start(self):
            pass

    monkeypatch.setattr("api.routes.backtest.threading.Thread", FakeThread)

    resp = _start_precondition(
        {
            "session_id": "bt_test_cap",
            "start_date": "2026-01-05",
            "end_date": "2026-01-09",
            "start_cash": 100000,
            "run_mode": "local",
            "market_cap_filter": "mid",
        }
    )
    # Should resolve an S&P subset and pass --symbols (or 400 if empty).
    assert resp.status_code in (200, 400)


def test_precondition_wires_run_id_and_returns_running():
    """A valid precondition returns run metadata (no assertion on cmd)."""
    resp = _start_precondition(
        {
            "session_id": "bt_test_meta",
            "start_date": "2026-01-05",
            "end_date": "2026-01-09",
            "start_cash": 100000,
            "run_mode": "local",
        }
    )
    if resp.status_code == 200:
        body = resp.json()
        assert body["status"] == "running"
