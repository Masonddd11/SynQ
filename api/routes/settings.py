"""Settings routes — /api/settings/* (local-only).

API keys and model settings are persisted locally to state/settings.json
via api.shared.read_settings()/write_settings(); model settings also apply
to the runtime through process environment variables that config.settings
(pydantic-settings) reads.
"""

import os

from fastapi import APIRouter

from api.shared import read_settings, write_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ─── API Keys ───────────────────────────────────────────────────────────────

_PLACEHOLDER_MARKERS = ("your_", "_here")


def _is_placeholder(value: str) -> bool:
    """True when a value is empty or a .env.example-style placeholder."""
    if not value:
        return True
    low = value.lower()
    return any(marker in low for marker in _PLACEHOLDER_MARKERS)


def _mask(value: str) -> str:
    """Apply the existing •••• masking convention."""
    return value[:4] + "••••" if len(value) > 4 else "••••"


def _effective_value(stored: str, env: str) -> str:
    """First real (non-placeholder) value among stored and env; '' if neither."""
    for candidate in (stored, env):
        if not _is_placeholder(candidate):
            return candidate
    return ""


@router.get("/keys")
def get_api_keys():
    """Get effective API keys (stored keys merged with .env fallbacks, masked).

    Effective = first real (non-placeholder) value among state/settings.json
    ['keys'] and config.settings (env truth), mirroring /api/config/alpaca.
    Placeholder or empty values are reported as unset (''), and secrets use
    the existing v[:4] + '••••' masking convention.
    """
    from config.settings import get_settings

    settings = read_settings()
    stored = settings.get("keys", {})
    s = get_settings()

    bridge = {
        "alpaca_paper_account_name": ("alpaca_paper_account_name", ""),
        "alpaca_paper_api_key": ("alpaca_paper_api_key", s.alpaca_api_key),
        "alpaca_paper_secret_key": ("alpaca_paper_secret_key", s.alpaca_secret_key),
        "alpaca_live_api_key": ("alpaca_live_api_key", ""),
        "alpaca_live_secret_key": ("alpaca_live_secret_key", ""),
        "polygon_api_key": ("polygon_api_key", s.polygon_api_key),
    }
    result = {}
    for field, (stored_key, env_val) in bridge.items():
        value = _effective_value(stored.get(stored_key, ""), env_val or "")
        is_secret = "secret" in field or "api_key" in field
        result[field] = _mask(value) if (value and is_secret) else value
    return result


@router.put("/keys")
def save_api_keys(body: dict):
    """Save API keys locally. Values containing '••••' are treated as unchanged."""
    settings = read_settings()
    existing = settings.get("keys", {})
    for k, v in body.items():
        if "••••" not in str(v):
            existing[k] = v
    settings["keys"] = existing
    write_settings(settings)
    return {"status": "saved"}


# ─── Model Settings ────────────────────────────────────────────────────────


@router.get("/model")
def get_model_settings():
    """Get current model configuration (runtime truth from .env / process env).

    The saved state/settings.json values are a dashboard override layer; the
    effective configuration is what config.settings resolves (env vars take
    precedence over .env defaults), so this returns the runtime values.
    """
    from config.settings import get_settings

    s = get_settings()
    return {
        "model_id": s.llm_model,
        "llm_provider": s.llm_provider,
        "llm_base_url": s.llm_base_url,
        "extended_thinking_enabled": s.extended_thinking_enabled,
        "extended_thinking_budget": s.extended_thinking_budget,
        "extended_thinking_effort": s.extended_thinking_effort,
    }


@router.put("/model")
def save_model_settings(body: dict):
    """Save model settings and apply to runtime."""
    from config.settings import get_settings

    s = get_settings()
    provider = body.get("llm_provider") or s.llm_provider
    if provider not in ("openai", "ollama"):
        provider = s.llm_provider  # validated: reject unknown providers

    settings = read_settings()
    settings["model"] = {
        "model_id": body.get("model_id", s.llm_model),
        "llm_provider": provider,
        "llm_base_url": body.get("llm_base_url", s.llm_base_url),
        "extended_thinking_enabled": body.get("extended_thinking_enabled", False),
        "extended_thinking_budget": body.get("extended_thinking_budget", 2048),
        "extended_thinking_effort": body.get("extended_thinking_effort", "medium"),
    }
    write_settings(settings)

    # config.settings reads these from process env — set them so the change
    # takes effect, then drop the cache so get_settings() re-reads them.
    os.environ["LLM_MODEL"] = settings["model"]["model_id"]
    os.environ["LLM_PROVIDER"] = settings["model"]["llm_provider"]
    os.environ["LLM_BASE_URL"] = settings["model"]["llm_base_url"]
    os.environ["EXTENDED_THINKING_ENABLED"] = str(settings["model"]["extended_thinking_enabled"]).lower()
    os.environ["EXTENDED_THINKING_BUDGET"] = str(settings["model"]["extended_thinking_budget"])
    os.environ["EXTENDED_THINKING_EFFORT"] = settings["model"]["extended_thinking_effort"]
    get_settings.cache_clear()

    return {"status": "saved", "model": settings["model"]}
