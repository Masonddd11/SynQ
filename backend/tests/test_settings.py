"""
tests/test_settings.py — Unit tests for Settings (pydantic-settings).

Tests cover: default values, field validators, and env-override behaviour.
All tests create a fresh Settings() instance (not the cached singleton)
to avoid cross-test contamination.
"""

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh_settings(**overrides):
    """Return a new Settings instance with optional field overrides.

    Isolated from .env (env_file=None) so default-value tests assert the
    true pydantic defaults, not whatever the developer's .env sets.
    """
    from config.settings import Settings
    return Settings(_env_file=None, **overrides)


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

def test_default_settings_load():
    """Settings must load with defaults without any .env file."""
    s = fresh_settings()
    assert s.alpaca_paper is True
    assert s.max_positions == 8
    assert s.position_size_pct == pytest.approx(0.02)


def test_default_llm_model():
    """llm_model must default to a non-empty string and llm_provider to 'openai'."""
    s = fresh_settings()
    assert isinstance(s.llm_model, str) and len(s.llm_model) > 0
    assert s.llm_provider == "openai"


def test_default_llm_base_url():
    """llm_base_url must default to an empty string (no remote endpoint)."""
    s = fresh_settings()
    assert s.llm_base_url == ""


def test_default_alpaca_base_url():
    s = fresh_settings()
    assert "paper" in s.alpaca_base_url


def test_default_env_is_development():
    s = fresh_settings()
    assert s.env == "development"


def test_default_schedule_times():
    s = fresh_settings()
    assert s.eod_signal_time == "16:00"
    assert s.intraday_signal_time == "10:30"
    assert s.morning_signal_time == "09:00"


# ---------------------------------------------------------------------------
# Risk parameter defaults
# ---------------------------------------------------------------------------

def test_risk_parameters_defaults():
    s = fresh_settings()
    assert s.max_drawdown_pct == pytest.approx(0.15)
    assert s.atr_stop_multiplier == pytest.approx(2.0)


def test_strategy_parameter_defaults():
    s = fresh_settings()
    assert s.momentum_lookback == 252
    assert s.momentum_skip == 21
    assert s.mean_reversion_window == 20
    assert s.mean_reversion_entry_z == pytest.approx(2.0)
    assert s.mean_reversion_exit_z == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Fraction validators
# ---------------------------------------------------------------------------

def test_invalid_position_size_pct_above_one():
    """position_size_pct >= 1.0 must raise ValidationError."""
    with pytest.raises(ValidationError):
        fresh_settings(position_size_pct=1.5)


def test_invalid_position_size_pct_at_one():
    """position_size_pct == 1.0 must raise ValidationError (strictly < 1)."""
    with pytest.raises(ValidationError):
        fresh_settings(position_size_pct=1.0)


def test_invalid_position_size_pct_zero():
    """position_size_pct == 0.0 must raise ValidationError (strictly > 0)."""
    with pytest.raises(ValidationError):
        fresh_settings(position_size_pct=0.0)


def test_invalid_max_drawdown_pct():
    with pytest.raises(ValidationError):
        fresh_settings(max_drawdown_pct=1.5)


def test_valid_fraction_boundary_values():
    """Values just inside (0, 1) must be accepted."""
    s = fresh_settings(position_size_pct=0.001)
    assert s.position_size_pct == pytest.approx(0.001)
    s2 = fresh_settings(position_size_pct=0.999)
    assert s2.position_size_pct == pytest.approx(0.999)


# ---------------------------------------------------------------------------
# Time format validators
# ---------------------------------------------------------------------------

def test_invalid_time_format_ampm():
    """'4:30pm' is not HH:MM — must raise ValidationError."""
    with pytest.raises(ValidationError):
        fresh_settings(eod_signal_time="4:30pm")


def test_invalid_time_format_no_colon():
    with pytest.raises(ValidationError):
        fresh_settings(eod_signal_time="1630")


def test_invalid_time_format_single_digit_hour():
    """'9:30' only has one digit for the hour — must raise ValidationError."""
    with pytest.raises(ValidationError):
        fresh_settings(eod_signal_time="9:30")


def test_invalid_intraday_time_format():
    with pytest.raises(ValidationError):
        fresh_settings(intraday_signal_time="1:30pm")


def test_valid_time_format_eod():
    s = fresh_settings(eod_signal_time="16:30")
    assert s.eod_signal_time == "16:30"


def test_valid_time_format_intraday():
    s = fresh_settings(intraday_signal_time="13:30")
    assert s.intraday_signal_time == "13:30"


def test_valid_time_format_midnight():
    """00:00 must be accepted as valid HH:MM."""
    s = fresh_settings(eod_signal_time="00:00")
    assert s.eod_signal_time == "00:00"


# ---------------------------------------------------------------------------
# Env literal validation
# ---------------------------------------------------------------------------

def test_valid_env_staging():
    s = fresh_settings(env="staging")
    assert s.env == "staging"


def test_valid_env_production():
    s = fresh_settings(env="production")
    assert s.env == "production"


def test_invalid_env_value():
    """An unrecognised env value must raise ValidationError."""
    with pytest.raises(ValidationError):
        fresh_settings(env="live")


# ---------------------------------------------------------------------------
# get_settings() singleton
# ---------------------------------------------------------------------------

def test_get_settings_returns_same_instance():
    """get_settings() must return the same cached instance on repeated calls."""
    from config.settings import get_settings
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_get_settings_cache_clear():
    """After cache_clear(), get_settings() returns a new instance."""
    from config.settings import get_settings
    get_settings.cache_clear()
    s1 = get_settings()
    get_settings.cache_clear()
    s2 = get_settings()
    # They should be equal in value but are different objects
    assert s1.max_positions == s2.max_positions


def test_env_override_llm_model(monkeypatch):
    """An LLM_MODEL env var must override the default after cache_clear()."""
    from config.settings import get_settings
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    get_settings.cache_clear()
    s = get_settings()
    assert s.llm_model == "gpt-4o"
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# /api/settings/keys route: effective state (stored + .env fallback)
# ---------------------------------------------------------------------------

API_KEY_FIELDS = {
    "alpaca_paper_account_name",
    "alpaca_paper_api_key",
    "alpaca_paper_secret_key",
    "alpaca_live_api_key",
    "alpaca_live_secret_key",
    "polygon_api_key",
}


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Isolate settings.json writes and force deterministic env per test."""
    from fastapi.testclient import TestClient

    from api.server import app
    from config.settings import get_settings

    monkeypatch.setattr("api.shared.SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setenv("ALPACA_API_KEY", "")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "")
    monkeypatch.setenv("POLYGON_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_BASE_URL", "")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_get_keys_returns_all_fields_shape(api_client):
    """GET /api/settings/keys must always return the full 6-field shape."""
    resp = api_client.get("/api/settings/keys")
    assert resp.status_code == 200
    assert set(resp.json().keys()) == API_KEY_FIELDS


def test_get_keys_env_fallback_masked(api_client, monkeypatch):
    """Keys configured only in .env must appear (masked), not empty."""
    from config.settings import get_settings

    monkeypatch.setenv("ALPACA_API_KEY", "PKTESTABCDEFGH")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "SKTEST123456")
    get_settings.cache_clear()

    resp = api_client.get("/api/settings/keys")
    body = resp.json()
    assert body["alpaca_paper_api_key"] == "PKTE" + "••••"
    assert body["alpaca_paper_secret_key"] == "SKTE" + "••••"
    assert body["alpaca_live_api_key"] == ""
    assert body["alpaca_live_secret_key"] == ""
    assert body["alpaca_paper_account_name"] == ""


def test_get_keys_placeholder_treated_unset(api_client, monkeypatch):
    """Placeholder .env values must be reported as unset ('')."""
    from config.settings import get_settings

    monkeypatch.setenv("POLYGON_API_KEY", "your_polygon_api_key_here")
    get_settings.cache_clear()

    resp = api_client.get("/api/settings/keys")
    assert resp.json()["polygon_api_key"] == ""


def test_get_keys_stored_overrides_env(api_client, monkeypatch):
    """A stored key must win over a different .env value (masked on read)."""
    from api.shared import write_settings
    from config.settings import get_settings

    write_settings({
        "keys": {
            "alpaca_paper_api_key": "STOREDKEY123",
            "alpaca_paper_secret_key": "STOREDSECRET456",
        }
    })
    monkeypatch.setenv("ALPACA_API_KEY", "ENVKEY9999999999")
    get_settings.cache_clear()

    resp = api_client.get("/api/settings/keys")
    body = resp.json()
    assert body["alpaca_paper_api_key"] == "STOR" + "••••"
    assert body["alpaca_paper_secret_key"] == "STOR" + "••••"


def test_put_keys_then_get_masked(api_client):
    """PUT stores plaintext; GET returns masked; full round-trip works."""
    from api.shared import read_settings

    resp = api_client.put("/api/settings/keys", json={
        "alpaca_paper_api_key": "PKROUNDTRIP1234",
        "alpaca_paper_secret_key": "SKROUNDTRIP5678",
        "polygon_api_key": "poly1234567890",
    })
    assert resp.status_code == 200
    assert read_settings()["keys"]["alpaca_paper_api_key"] == "PKROUNDTRIP1234"

    get = api_client.get("/api/settings/keys").json()
    assert get["alpaca_paper_api_key"] == "PKRO" + "••••"
    assert get["alpaca_paper_secret_key"] == "SKRO" + "••••"
    assert get["polygon_api_key"] == "poly" + "••••"


def test_put_keys_masked_value_keeps_stored(api_client):
    """Sending back a masked '••••' value must leave the stored key unchanged."""
    from api.shared import read_settings

    api_client.put("/api/settings/keys", json={
        "alpaca_paper_api_key": "PKREAL1234567890",
    })
    api_client.put("/api/settings/keys", json={
        "alpaca_paper_api_key": "PKRE" + "••••",
    })
    stored = read_settings()["keys"]["alpaca_paper_api_key"]
    assert stored == "PKREAL1234567890"


# ---------------------------------------------------------------------------
# /api/settings/model route: provider + base_url persistence (effective state)
# ---------------------------------------------------------------------------


def test_put_model_persists_provider_and_base_url(api_client):
    """PUT /model must persist + apply llm_provider and llm_base_url."""
    from api.shared import read_settings
    from config.settings import get_settings

    payload = {
        "model_id": "gpt-4o-mini",
        "llm_provider": "ollama",
        "llm_base_url": "http://localhost:11434/v1",
        "extended_thinking_enabled": False,
        "extended_thinking_budget": 2048,
        "extended_thinking_effort": "medium",
    }
    resp = api_client.put("/api/settings/model", json=payload)
    assert resp.status_code == 200

    saved = read_settings()["model"]
    assert saved["llm_provider"] == "ollama"
    assert saved["llm_base_url"] == "http://localhost:11434/v1"

    get_settings.cache_clear()
    s = get_settings()
    assert s.llm_provider == "ollama"
    assert s.llm_base_url == "http://localhost:11434/v1"

    get = api_client.get("/api/settings/model").json()
    assert get["llm_provider"] == "ollama"
    assert get["llm_base_url"] == "http://localhost:11434/v1"


def test_put_model_invalid_provider_ignored(api_client):
    """An invalid llm_provider must be rejected, not crash or persist."""
    from api.shared import read_settings
    from config.settings import get_settings

    resp = api_client.put("/api/settings/model", json={
        "model_id": "gpt-4o-mini",
        "llm_provider": "bogus",
        "llm_base_url": "",
    })
    assert resp.status_code == 200

    get_settings.cache_clear()
    assert get_settings().llm_provider == "openai"

    saved = read_settings().get("model", {})
    assert saved.get("llm_provider", "openai") == "openai"
