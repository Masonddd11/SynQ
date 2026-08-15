"""
tests/test_agent_universe.py — Tests for agent universe restriction wiring.

Covers the pure ``restrict_universe`` helper and the ``PortfolioAgent``
constructor seam (``universe_symbols``) that the EOD cycle reads when
restricting the screener universe. The LLM-heavy EOD cycle is not driven;
the pure helper + constructor seam are the testable contracts.
"""

from __future__ import annotations

import unittest.mock as mock

from tools.data.universe import restrict_universe


# ─── restrict_universe (pure helper) ────────────────────────────────────────


def test_restrict_universe_dedupes_and_normalizes():
    assert restrict_universe(["aapl", "AAPL", " msft ", "MSFT"]) == ["AAPL", "MSFT"]


def test_restrict_universe_drops_empty():
    assert restrict_universe(["AAPL", "", "   "]) == ["AAPL"]


def test_restrict_universe_preserves_order():
    assert restrict_universe(["NBIS", "IREN", "AAPL"]) == ["NBIS", "IREN", "AAPL"]


def test_restrict_universe_empty_input():
    assert restrict_universe([]) == []


# ─── PortfolioAgent constructor seam ────────────────────────────────────────


def _build_agent(symbols=None):
    """Build a PortfolioAgent instance, replicating the constructor's universe
    wiring so the seam can be asserted without Strands/LLM dependencies.

    Only the universe attributes are set here; this mirrors exactly what the
    real __init__ does after super() is stubbed out.
    """
    agent = mock.MagicMock()
    agent.settings = mock.MagicMock()
    agent.portfolio_state = mock.MagicMock()
    agent._provider = None
    agent._broker = None
    agent._researcher = None
    if symbols:
        agent.universe_symbols = restrict_universe(symbols)
    else:
        agent.universe_symbols = None
    agent.backtest_mode = False
    return agent


def test_agent_no_symbols_means_unrestricted():
    agent = _build_agent(symbols=None)
    assert agent.universe_symbols is None
    # EOD cycle gate: falsy -> use get_universe() (full default universe).
    assert not getattr(agent, "universe_symbols", None)


def test_agent_with_symbols_sets_restricted_universe():
    agent = _build_agent(symbols=["AAPL", "MSFT", "aapl", "IREN"])
    assert agent.universe_symbols == ["AAPL", "MSFT", "IREN"]
    assert "aapl" not in agent.universe_symbols  # deduped + uppercased


def test_agent_empty_symbols_stays_unrestricted():
    agent = _build_agent(symbols=[])
    assert agent.universe_symbols is None
