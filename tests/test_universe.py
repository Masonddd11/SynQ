"""
tests/test_universe.py — Unit tests for tools/data/universe.py.

Tests market-cap classification boundaries and universe resolution
(source selection, missing reporting, cap filtering, always-include).
All pure — no network, no fixture file reads.
"""

from __future__ import annotations

import pytest

from tools.data.universe import (
    HIGH,
    LOW,
    MID,
    UniverseResolution,
    classify_market_cap,
    resolve_universe,
)

LOW_MAX = 2_000_000_000
MID_MAX = 10_000_000_000

# Small synthetic "available" universe for resolution tests.
AVAILABLE = {"AAPL", "MSFT", "IREN", "NBIS", "SPY", "QQQ"}


# ─── classify_market_cap boundaries ──────────────────────────────────────────


@pytest.mark.parametrize(
    "cap, expected",
    [
        (0, LOW),
        (LOW_MAX - 1, LOW),
        # Exact boundary -> next bucket (low is [0, low_max), mid is [low_max, mid_max))
        (LOW_MAX, MID),
        (LOW_MAX + 1, MID),
        (MID_MAX - 1, MID),
        (MID_MAX, HIGH),
        (MID_MAX + 1, HIGH),
        (1e15, HIGH),
        (None, None),
    ],
)
def test_classify_market_cap_buckets(cap, expected):
    assert classify_market_cap(cap, LOW_MAX, MID_MAX) == expected


# ─── resolve_universe: source selection ──────────────────────────────────────


def test_resolve_sp500_uses_fixture_based_eligible(monkeypatch):
    """source='sp500' resolves against the available set (fixture subset)."""
    # Mock the fixture loader so the test is hermetic.
    fixture_symbols = ["AAPL", "MSFT", "TSLA", "GOOG"]
    monkeypatch.setattr(
        "tools.data.universe._sp500_fixture_symbols",
        lambda: fixture_symbols,
    )
    res = resolve_universe("sp500", None, None, available=AVAILABLE)
    assert isinstance(res, UniverseResolution)
    # Only SP500 names that are available resolve; SPY/QQQ forced in.
    assert "AAPL" in res.symbols
    assert "MSFT" in res.symbols
    assert "SPY" in res.symbols
    assert "QQQ" in res.symbols
    # TSLA/GOOG not available -> missing.
    assert "TSLA" in res.missing
    assert "GOOG" in res.missing


def test_resolve_custom_uses_requested_symbols():
    """source='custom' uses exactly the requested symbols (normalized)."""
    res = resolve_universe("custom", ["aapl", " MSFT ", "IREN"], None, available=AVAILABLE)
    assert res.symbols == ["AAPL", "MSFT", "IREN", "SPY", "QQQ"]
    assert res.missing == []


def test_resolve_custom_reports_missing_only():
    """Custom symbols without fixture data are reported and excluded."""
    res = resolve_universe("custom", ["IREN", "ZZZZ"], None, available=AVAILABLE)
    assert "IREN" in res.symbols
    assert "ZZZZ" in res.missing
    assert "ZZZZ" not in res.symbols


def test_resolve_custom_dedupes_and_normalizes():
    res = resolve_universe("custom", ["aapl", "AAPL", " MSFT ", "aapl"], None, available=AVAILABLE)
    # Order-preserving, deduped, uppercase.
    assert res.symbols[:2] == ["AAPL", "MSFT"]


def test_resolve_unknown_source_raises():
    with pytest.raises(ValueError):
        resolve_universe("bogus", None, None, available=AVAILABLE)


def test_resolve_default_no_symbols_keeps_always_include():
    """Empty custom request still resolves to just the always-include set."""
    res = resolve_universe("custom", [], None, available=AVAILABLE)
    assert set(res.symbols) == {"SPY", "QQQ"}


# ─── resolve_universe: market-cap filter ────────────────────────────────────


def test_resolve_market_cap_filter_subsets():
    caps = {
        "AAPL": 3_000_000_000_000,  # high
        "MSFT": 50_000_000_000,  # high
        "IREN": 1_000_000_000,  # low
        "NBIS": 5_000_000_000,  # mid
    }
    res = resolve_universe(
        "custom",
        ["AAPL", "MSFT", "IREN", "NBIS"],
        MID,
        available=AVAILABLE,
        caps=caps,
    )
    # Only mid-cap names survive (plus SPY/QQQ always-include, mid too).
    assert "NBIS" in res.symbols
    assert "AAPL" not in res.symbols
    assert "IREN" not in res.symbols


def test_resolve_market_cap_low_bucket():
    caps = {"IREN": 1_000_000_000, "NBIS": 5_000_000_000}
    res = resolve_universe("custom", ["IREN", "NBIS"], LOW, available=AVAILABLE, caps=caps)
    assert "IREN" in res.symbols
    assert "NBIS" not in res.symbols


def test_resolve_market_cap_unknown_excluded_and_reported():
    caps = {"IREN": 1_000_000_000, "NBIS": None}
    res = resolve_universe(
        "custom", ["IREN", "NBIS"], MID, available=AVAILABLE, caps=caps
    )
    assert res.unknown_cap == ["NBIS"]
    assert "NBIS" not in res.symbols


def test_resolve_market_cap_none_keeps_all_without_unknown_list():
    caps = {"IREN": 1_000_000_000, "NBIS": None}
    res = resolve_universe("custom", ["IREN", "NBIS"], None, available=AVAILABLE, caps=caps)
    assert set(res.symbols) >= {"IREN", "NBIS"}
    assert res.unknown_cap == []
