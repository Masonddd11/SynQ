"""Universe routes — shared symbol-restriction config + available checklist.

API for the sidebar "Universe" page that holds the enabled symbol list which
acts as a common restricter across backtesting, paper trading, and live trading:
    GET  /api/universe            -> current persisted restriction
    PUT  /api/universe            -> save a new enabled list
    GET  /api/universe/available  -> the candidate checklist (S&P 500 universe)
    GET  /api/universe/meta       -> per-symbol sector + market-cap metadata

When the persisted list is non-empty every mode restricts to it; an empty list
means the full default universe (S&P 500), preserving current behaviour.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from state import universe as universe_store  # module ref so tests can patch

router = APIRouter(prefix="/api/universe", tags=["universe"])


# ─── Request model ──────────────────────────────────────────────────────────


class UniverseUpdate(BaseModel):
    symbols: list[str] = []


# ─── Helpers ────────────────────────────────────────────────────────────────


def _sector_map() -> dict[str, str]:
    """Load the S&P 500 sector mapping from the local Wikipedia fixture."""
    try:
        from backtest.fixtures.loader import load_fixture
        raw: dict[str, str] = load_fixture("wikipedia/sp500_sectors.json")
        return {k.upper(): v for k, v in raw.items()}
    except Exception:
        return {}


def _get_cached_caps() -> dict[str, float]:
    """Read the market-cap disk cache (populated by yfinance fetch_market_caps)."""
    from tools.data.universe import _load_cached_caps
    return _load_cached_caps()


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get("")
def get_universe():
    """Return the current persisted symbol restriction."""
    loaded = universe_store.get_universe_store().load()
    return {"symbols": loaded["symbols"], "updated_at": loaded.get("updated_at", "")}


@router.put("")
def put_universe(req: UniverseUpdate):
    """Persist a new enabled symbol list. Empty list = unrestricted."""
    doc = universe_store.save_restricted_symbols(req.symbols)
    return {"symbols": doc["symbols"], "updated_at": doc["updated_at"]}


@router.get("/available")
def get_available():
    """Return the candidate S&P 500 universe for the checklist.

    Response includes per-symbol ``sector`` so the frontend can group and
    filter by GICS sector without a second request.
    """
    from tools.data import screener

    try:
        tickers = [t.upper() for t in screener.get_sp500_tickers()]
    except Exception as exc:  # pragmatic: a checkout without network still resolves
        raise HTTPException(502, f"Unable to load S&P 500 universe: {exc}")

    # Deterministic, deduped, ordered.
    seen: set[str] = set()
    ordered: list[str] = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            ordered.append(t)

    sectors = _sector_map()
    return {
        "symbols": ordered,
        "count": len(ordered),
        "sectors": sectors,
    }


@router.get("/meta")
def get_meta():
    """Return per-symbol sector and cached market-cap for all S&P 500 symbols.

    Market caps come from the local disk cache only (no live yfinance in the
    request path).  ``marketCap`` is ``null`` when no cached value exists.
    """
    from tools.data.universe import classify_market_cap
    from config.settings import get_settings

    tickers = get_available().get("symbols", [])
    sectors = _sector_map()
    caps = _get_cached_caps()
    settings = get_settings()

    meta: dict[str, dict] = {}
    for t in tickers:
        cap_val = caps.get(t)
        bucket = classify_market_cap(cap_val, settings.market_cap_low_max, settings.market_cap_mid_max)
        meta[t] = {
            "sector": sectors.get(t, ""),
            "marketCap": cap_val,
            "marketCapBucket": bucket,  # "low" | "mid" | "high" | null
        }
    return meta
