"""
tools/data/universe.py — Backtest universe selection and market-cap buckets.

Resolves a user's chosen stock universe (S&P 500 preset, or a set of custom
symbols) against the symbols that actually have fixture bar data, optionally
filtered by a market-cap bucket (low / mid / high).

This is a pure data module, separate from the EOD ``screen_universe`` in
``backtest/common.py``: this one decides *which symbols are eligible* for a
backtest before the engine's liquidity/volatility screener runs.

Market-cap values are fetched from yfinance and cached to disk (``.cache``)
with a ~24h TTL so the filter is fast and does not hammer the upstream API.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# JSON cache of symbol -> market cap (USD), keyed in the settings cache dir.
_CAPS_DIR = Path(os.environ.get("UNIVERSE_CACHE_DIR", "backend/.cache"))
_CAPS_FILE = _CAPS_DIR / "market_caps.json"
_CAPS_TTL_SECONDS = 24 * 3600

# Bucket labels (used by the API and reflected in settings thresholds).
LOW = "low"
MID = "mid"
HIGH = "high"
BUCKETS = (LOW, MID, HIGH)

# Benchmarks/breadth are always included so backtest metrics (SPY comparison)
# and breadth context keep working regardless of the selected universe.
_ALWAYS_INCLUDE = ("SPY", "QQQ")


@dataclass
class UniverseResolution:
    """Result of resolving a requested universe against available symbol data.

    Attributes:
        symbols: Resolved, eligible symbols (uppercase, deduped, order-preserving).
        missing: Requested symbols with no fixture bars (data gap).
        unknown_cap: Requested symbols whose market cap is unknown; only
            populated when a market-cap filter is active.
    """

    symbols: list[str]
    missing: list[str]
    unknown_cap: list[str] = field(default_factory=list)


def classify_market_cap(
    market_cap: float | None,
    low_max: float,
    mid_max: float,
) -> str | None:
    """Bucket a market cap into ``low`` / ``mid`` / ``high``.

    ``None`` (unknown) returns ``None`` — the caller decides how to treat
    symbols without a cap (excluded under the active filter).
    """
    if market_cap is None:
        return None
    if market_cap < low_max:
        return LOW
    if market_cap < mid_max:
        return MID
    return HIGH


def _load_cached_caps() -> dict[str, float]:
    """Load the market-cap cache if present and fresh."""
    try:
        if not _CAPS_FILE.exists():
            return {}
        if time.time() - _CAPS_FILE.stat().st_mtime > _CAPS_TTL_SECONDS:
            logger.info("Market-cap cache is stale; ignoring")
            return {}
        with open(_CAPS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return {str(k).upper(): float(v) for k, v in data.items()}
    except Exception as exc:  # never break the API on a corrupt cache
        logger.warning("Failed to read market-cap cache: %s", exc)
        return {}


def _save_cached_caps(caps: dict[str, float]) -> None:
    try:
        _CAPS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_CAPS_FILE, "w", encoding="utf-8") as f:
            json.dump(caps, f, indent=2)
    except Exception as exc:
        logger.warning("Failed to write market-cap cache: %s", exc)


def fetch_market_caps(symbols: list[str]) -> dict[str, float | None]:
    """Fetch market caps for ``symbols`` via yfinance, cached to disk.

    Cache hit symbols are returned immediately (no network). Missing symbols
    are fetched in a throttled batch; failures become ``None`` and are merged
    into the cache. Never raises — a failed fetch yields ``None`` for that
    symbol so the resolver degrades gracefully.
    """
    if not symbols:
        return {}

    cache = _load_cached_caps()
    result: dict[str, float | None] = {s: cache.get(s) for s in symbols}

    to_fetch = [s for s in symbols if s not in cache]
    if not to_fetch:
        return result

    try:
        import time as _time
        import yfinance as yf

        fresh: dict[str, float | None] = {}
        # Batch by 50 with a short delay between batches to avoid rate limits.
        for i in range(0, len(to_fetch), 50):
            batch = to_fetch[i : i + 50]
            for symbol in batch:
                try:
                    info = yf.Ticker(symbol).info
                    value = info.get("marketCap")
                    fresh[symbol] = float(value) if value else None
                except Exception as exc:
                    logger.warning("Market cap fetch failed for %s: %s", symbol, exc)
                    fresh[symbol] = None
            if i + 50 < len(to_fetch):
                _time.sleep(0.5)

        # Merge fresh values; persist only known caps (unknowns stay out of
        # the cache so the next resolve retries them).
        known = {s: v for s, v in fresh.items() if v is not None}
        if known:
            _save_cached_caps({**cache, **known})
        return {**result, **fresh}
    except Exception as exc:
        logger.warning("Market cap batch fetch failed: %s", exc)
        return result


def _sp500_fixture_symbols() -> list[str]:
    """S&P 500 constituent tickers from the local wiki fixture (no network)."""
    from backtest.fixtures.loader import load_fixture

    try:
        raw = load_fixture("wikipedia/sp500_tickers.json")
        return [str(t).upper() for t in raw]
    except FileNotFoundError:
        from tools.data.screener import get_sp500_tickers

        logger.warning("S&P 500 fixture missing; falling back to live/embedded list")
        return [t.upper() for t in get_sp500_tickers()]


def resolve_universe(
    source: str,
    symbols: list[str] | None,
    market_cap: str | None,
    available: set[str],
    caps: dict[str, float | None] | None = None,
    low_max: float = 2_000_000_000,
    mid_max: float = 10_000_000_000,
    always_include: tuple[str, ...] = _ALWAYS_INCLUDE,
) -> UniverseResolution:
    """Resolve a requested universe to eligible symbols for a backtest.

    Args:
        source: ``"sp500"`` (use the fixture S&P 500 list) or ``"custom"``
            (use ``symbols`` exactly).
        symbols: Requested symbols, only meaningful when ``source == "custom"``.
        market_cap: Optional bucket filter: ``"low" | "mid" | "high" | None``.
        available: Set of symbols that actually have fixture data.
        caps: Symbol -> market cap (USD) mapping; ``None`` values mean unknown.
        low_max/mid_max: Market-cap bucket boundaries (from settings).
        always_include: Symbols always kept (SPY/QQQ for benchmark/breadth),
            regardless of eligibility or the market-cap filter.

    Returns:
        A :class:`UniverseResolution` with eligible ``symbols`` plus reporting
        lists for missing / unknown-cap names.
    """
    available = {t.upper() for t in available}

    if source == "sp500":
        base = _sp500_fixture_symbols()
    elif source == "custom":
        base = list(symbols or [])
    else:
        raise ValueError(f"Unknown universe source: {source}")

    # Normalize + dedupe, order-preserving.
    seen: set[str] = set()
    requested: list[str] = []
    for t in base:
        up = t.strip().upper()
        if not up:
            continue
        if up not in seen:
            seen.add(up)
            requested.append(up)

    # Report requested-but-missing (data gap), excluding always-include names.
    missing = [t for t in requested if t not in available and t not in always_include]

    # Eligible = requested ∩ available. Always-include names (SPY/QQQ) are
    # infrastructure for benchmark/breadth and are never filtered or reported.
    eligible = [t for t in requested if t in available]
    always_kept = [t for t in always_include if t in available]

    unknown_cap: list[str] = []
    if market_cap in BUCKETS:
        caps = caps or {}
        bucket_map = {
            t: classify_market_cap(caps.get(t), low_max, mid_max)
            for t in eligible
        }
        filtered = [t for t in eligible if bucket_map[t] == market_cap]
        unknown_cap = [t for t in eligible if bucket_map[t] is None]
        resolved = filtered + always_kept
    else:
        # No bucket filter: unknown caps are irrelevant, keep everything eligible.
        resolved = eligible + always_kept

    # Final deterministic order: requested eligible symbols first (as requested),
    # then any always-include names not already present.
    final: list[str] = []
    for t in resolved:
        if t not in final:
            final.append(t)
    return UniverseResolution(symbols=final, missing=missing, unknown_cap=unknown_cap)


def restrict_universe(symbols: list[str]) -> list[str]:
    """Normalize a restriction list: order-preserving, deduped, uppercased.

    Used by the agent (PortfolioAgent) to know exactly which symbols if may
    trade when a universe restriction is active. Empty tokens are dropped.
    """
    return list(dict.fromkeys(s.strip().upper() for s in symbols if s.strip()))

