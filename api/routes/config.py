"""Config routes — /api/config/* (local-only deployment)"""

from fastapi import APIRouter

from api.shared import read_settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/mode")
def get_mode():
    """Return current deployment mode (always local)."""
    return {"mode": "local"}


@router.get("/alpaca")
def get_alpaca_status():
    """Check if Alpaca API keys are configured (not default placeholders).

    Keys may live in state/settings.json (saved from the dashboard) or in
    .env (read via config.settings) — either source counts as configured.
    """
    from config.settings import get_settings

    settings = read_settings()
    keys = settings.get("keys", {})
    s = get_settings()

    paper_key = keys.get("alpaca_paper_api_key") or s.alpaca_api_key
    paper_secret = keys.get("alpaca_paper_secret_key") or s.alpaca_secret_key
    paper_configured = bool(paper_key and paper_secret)
    live_configured = bool(
        keys.get("alpaca_live_api_key") and keys.get("alpaca_live_secret_key")
    )
    return {
        "configured": paper_configured,
        "paper_configured": paper_configured,
        "live_configured": live_configured,
    }
