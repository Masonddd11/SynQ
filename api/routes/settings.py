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


@router.get("/keys")
def get_api_keys():
    """Get stored API keys (secrets are masked)."""
    settings = read_settings()
    keys = settings.get("keys", {})
    masked = {}
    for k, v in keys.items():
        if ("secret" in k or "api_key" in k) and v:
            masked[k] = v[:4] + "••••" if len(v) > 4 else "••••"
        else:
            masked[k] = v
    return masked


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

    settings = read_settings()
    settings["model"] = {
        "model_id": body.get("model_id", get_settings().llm_model),
        "extended_thinking_enabled": body.get("extended_thinking_enabled", False),
        "extended_thinking_budget": body.get("extended_thinking_budget", 2048),
        "extended_thinking_effort": body.get("extended_thinking_effort", "medium"),
    }
    write_settings(settings)

    # config.settings reads these from process env — set them so the change
    # takes effect, then drop the cache so get_settings() re-reads them.
    os.environ["LLM_MODEL"] = settings["model"]["model_id"]
    os.environ["EXTENDED_THINKING_ENABLED"] = str(settings["model"]["extended_thinking_enabled"]).lower()
    os.environ["EXTENDED_THINKING_BUDGET"] = str(settings["model"]["extended_thinking_budget"])
    os.environ["EXTENDED_THINKING_EFFORT"] = settings["model"]["extended_thinking_effort"]
    get_settings.cache_clear()

    return {"status": "saved", "model": settings["model"]}
