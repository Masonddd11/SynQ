"""
tests/test_backtest_cli.py — Tests for backtest universe restriction.

Verifies ``Backtest._universe_symbols()`` helper and the CLI ``--symbols``
handling: default == full available set, subset == requested-∩-available
(+ always-include SPY/QQQ), all-unknown raises a clear ValueError.
"""

from __future__ import annotations

import pytest

from backtest.backtest import Backtest


class _FakeProvider:
    """Minimal stand-in exposing only what universe resolution touches."""

    def __init__(self, symbols):
        self.available_symbols = list(symbols)


def _make_bt(symbols=None, available=None):
    """Build a Backtest without running the heavy __init__."""
    bt = object.__new__(Backtest)
    bt.provider = _FakeProvider(available or ["AAPL", "MSFT", "IREN", "SPY", "QQQ"])
    bt.symbols = symbols
    bt._universe = None
    return bt


def test_universe_default_is_full_available_set():
    bt = _make_bt(symbols=None)
    assert set(bt._universe_symbols()) == {"AAPL", "MSFT", "IREN", "SPY", "QQQ"}


def test_universe_subset_restricts_and_keeps_benchmark():
    bt = _make_bt(symbols=["AAPL", "MSFT"], available=["AAPL", "MSFT", "IREN", "SPY", "QQQ"])
    universe = bt._universe_symbols()
    # Only requested-available plus always-include SPY/QQQ survive.
    assert set(universe) == {"AAPL", "MSFT", "SPY", "QQQ"}
    assert "IREN" not in universe


def test_universe_dedupes_and_normalizes_case():
    bt = _make_bt(symbols=["aapl", "AAPL", " msft "], available=["AAPL", "MSFT", "SPY", "QQQ"])
    universe = bt._universe_symbols()
    assert universe.count("AAPL") == 1
    assert universe.count("MSFT") == 1
    assert set(universe) == {"AAPL", "MSFT", "SPY", "QQQ"}


def test_universe_all_unknown_raises_value_error():
    bt = _make_bt(symbols=["ZZZZ", "YYYY"], available=["AAPL", "SPY", "QQQ"])
    with pytest.raises(ValueError, match="None of the requested symbols"):
        bt._universe_symbols()


def test_universe_partial_unknown_drops_only_missing():
    bt = _make_bt(symbols=["AAPL", "ZZZZ"], available=["AAPL", "SPY", "QQQ"])
    universe = bt._universe_symbols()
    assert "AAPL" in universe
    assert "ZZZZ" not in universe


def test_cli_symbols_split_handles_spaces():
    """The CLI splits comma strings; whitespace is stripped per token."""
    from backtest import backtest as mod

    # Parse like args.symbols.split(",") does.
    raw = " AAPL , MSFT "
    parsed = raw.split(",")
    bt = _make_bt(symbols=parsed or None, available=["AAPL", "MSFT", "SPY", "QQQ"])
    assert "AAPL" in bt._universe_symbols()
    assert "MSFT" in bt._universe_symbols()
    assert mod is not None  # module import is healthy
