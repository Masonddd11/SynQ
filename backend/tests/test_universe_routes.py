"""
tests/test_universe_routes.py — API contract tests for /api/universe.

Covers GET/PUT persistence, empty==unrestricted, and the available checklist.
Uses a tmp-path store and a stubbed S&P 500 ticker source (no network).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.server import app
from state.universe import UniverseStore

client = TestClient(app)

# A small, deterministic candidate universe for the checklist tests.
FAKE_SP500 = ["AAPL", "MSFT", "GOOGL", "GOOG", "SPY"]


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    """Point the universe store at a tmp file so tests never touch real state."""
    store = UniverseStore(tmp_path / "universe.json")
    monkeypatch.setattr("state.universe.get_universe_store", lambda: store)
    yield store


@pytest.fixture(autouse=True)
def _stub_sp500(monkeypatch):
    monkeypatch.setattr(
        "tools.data.screener.get_sp500_tickers", lambda: list(FAKE_SP500)
    )
    yield


@pytest.fixture(autouse=True)
def _stub_sectors_and_caps(monkeypatch):
    """Hermetic sector map + market-cap cache for the meta/available endpoints."""
    monkeypatch.setattr(
        "api.routes.universe._sector_map",
        lambda: {"AAPL": "Information Technology", "MSFT": "Information Technology", "GOOGL": "Communication", "GOOG": "Communication", "SPY": ""},
    )
    monkeypatch.setattr(
        "api.routes.universe._get_cached_caps",
        lambda: {"AAPL": 4_000_000_000_000, "MSFT": 3_000_000_000, "GOOGL": 1_000_000_000},
    )
    yield


def test_get_empty_universe_by_default():
    resp = client.get("/api/universe")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbols"] == []
    assert "updated_at" in body


def test_put_then_get_roundtrip():
    put = client.put("/api/universe", json={"symbols": ["AAPL", "MSFT", "IREN"]})
    assert put.status_code == 200
    saved = put.json()
    assert saved["symbols"] == ["AAPL", "MSFT", "IREN"]
    assert saved["updated_at"]

    get = client.get("/api/universe")
    assert get.json()["symbols"] == ["AAPL", "MSFT", "IREN"]


def test_put_normalizes_and_dedupes():
    resp = client.put("/api/universe", json={"symbols": ["aapl", "AAPL", " msft "]}).json()
    assert resp["symbols"] == ["AAPL", "MSFT"]


def test_put_empty_means_unrestricted():
    client.put("/api/universe", json={"symbols": ["AAPL"]})
    resp = client.put("/api/universe", json={"symbols": []})
    assert resp.status_code == 200
    assert resp.json()["symbols"] == []
    assert client.get("/api/universe").json()["symbols"] == []


def test_available_returns_deduped_sorted_checklist():
    resp = client.get("/api/universe/available")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == len(FAKE_SP500)
    # duplicates removed, order preserved
    assert body["symbols"] == FAKE_SP500


def test_available_includes_sector_map():
    resp = client.get("/api/universe/available")
    body = resp.json()
    assert "sectors" in body
    assert body["sectors"]["AAPL"] == "Information Technology"


def test_meta_returns_sector_and_cap_bucket():
    resp = client.get("/api/universe/meta")
    assert resp.status_code == 200
    meta = resp.json()
    # AAPL is high cap (> $10B) in the stub.
    assert meta["AAPL"]["sector"] == "Information Technology"
    assert meta["AAPL"]["marketCapBucket"] == "high"
    # MSFT is mid cap ($2B–$10B).
    assert meta["MSFT"]["marketCapBucket"] == "mid"
    # Symbol with no cached cap -> None bucket.
    assert meta["SPY"]["marketCapBucket"] is None
