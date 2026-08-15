"""
tests/test_system_routes.py — API contract tests for the /api/system endpoints.

TDD step 1: these tests define the contract for
  GET /api/system/health
  GET /api/system/log
They are expected to FAIL (404) until the routes are implemented.
"""

from __future__ import annotations

import types

from fastapi.testclient import TestClient

from api.server import app


client = TestClient(app)

# Accepted status values, per the planned contract.
OVERALL_STATUSES = {'ok', 'degraded', 'down'}
SERVICE_STATUSES = {'ok', 'degraded', 'down', 'idle', 'not_configured'}


def test_health_endpoint():
    """GET /api/system/health -> 200 with a health summary."""
    resp = client.get('/api/system/health')

    assert resp.status_code == 200
    body = resp.json()

    assert isinstance(body['timestamp'], str)
    assert body['overall'] in OVERALL_STATUSES

    services = body['services']
    assert isinstance(services, list)
    assert len(services) > 0
    for service in services:
        assert isinstance(service['name'], str)
        assert service['status'] in SERVICE_STATUSES
        assert 'detail' in service


def test_log_endpoint():
    """GET /api/system/log?limit=50 -> 200 with a source per log stream."""
    resp = client.get('/api/system/log', params={'limit': 50})

    assert resp.status_code == 200
    body = resp.json()

    sources = body['sources']
    assert isinstance(sources, list)
    for source in sources:
        assert isinstance(source['name'], str)
        assert isinstance(source['path'], str)
        lines = source['lines']
        assert isinstance(lines, list)
        for line in lines:
            assert isinstance(line, str)


def test_log_no_active_sessions():
    """GET /api/system/log without limit -> 200, sources is a list (may be empty).

    The endpoint must tolerate zero active sessions and never error.
    """
    resp = client.get('/api/system/log')

    assert resp.status_code == 200
    body = resp.json()

    assert isinstance(body['sources'], list)


# ─── POST /api/system/check/{service} (TDD step 1: expected 404 until implemented) ───


def test_check_unknown_service_404():
    """POST /api/system/check/doesnotexist -> 404 (unknown service)."""
    resp = client.post('/api/system/check/doesnotexist')

    assert resp.status_code == 404


def test_check_store_roundtrip():
    """POST /api/system/check/store -> 200 with a store round-trip result."""
    resp = client.post('/api/system/check/store')

    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == {'service', 'ok', 'status', 'latency_ms', 'detail', 'error'}
    assert body['service'] == 'store'
    assert body['ok'] is True
    assert body['status'] == 'ok'
    # The round-trip is a single fs write/read/unlink; coarse clocks may
    # truncate the elapsed time to 0, so allow >= 0 here.
    assert body['latency_ms'] >= 0
    assert body['error'] is None


def test_check_cache_roundtrip():
    """POST /api/system/check/cache -> 200 with a cache put/get round-trip."""
    resp = client.post('/api/system/check/cache')

    assert resp.status_code == 200
    body = resp.json()

    assert body['ok'] is True
    assert body['status'] == 'ok'
    assert body['latency_ms'] >= 0
    assert body['error'] is None


def test_check_scheduler_no_session(monkeypatch):
    """POST /api/system/check/scheduler -> 200, idle when no active paper session."""
    monkeypatch.setattr('api.routes.system._active_paper_session', lambda: None)
    resp = client.post('/api/system/check/scheduler')

    assert resp.status_code == 200
    body = resp.json()

    assert body['status'] == 'idle'
    assert body['ok'] is True
    assert 'No active paper session' in body['detail']


def test_check_data_ok():
    """POST /api/system/check/data -> 200 ok when fixtures are present."""
    resp = client.post('/api/system/check/data')

    assert resp.status_code == 200
    body = resp.json()

    assert body['ok'] is True
    assert body['status'] == 'ok'
    assert body['error'] is None


def test_check_llm_not_configured(monkeypatch):
    """POST /api/system/check/llm -> 200 not_configured when LLM keys are empty."""
    monkeypatch.setattr(
        'api.routes.system.get_settings',
        lambda: types.SimpleNamespace(
            llm_base_url="", llm_api_key="", llm_model="",
            alpaca_api_key="x", alpaca_secret_key="x",
            session_dir="", cache_dir="",
        ),
    )
    resp = client.post('/api/system/check/llm')

    assert resp.status_code == 200
    body = resp.json()

    assert body['ok'] is False
    assert body['status'] == 'not_configured'


def test_check_broker_not_configured(monkeypatch):
    """POST /api/system/check/broker -> 200 not_configured when Alpaca keys are empty."""
    monkeypatch.setattr(
        'api.routes.system.get_settings',
        lambda: types.SimpleNamespace(
            llm_base_url="x", llm_api_key="x", llm_model="",
            alpaca_api_key="", alpaca_secret_key="",
            session_dir="", cache_dir="",
        ),
    )
    resp = client.post('/api/system/check/broker')

    assert resp.status_code == 200
    body = resp.json()

    assert body['ok'] is False
    assert body['status'] == 'not_configured'


def test_check_api_schema(monkeypatch):
    """POST /api/system/check/api -> 200 with the exact response schema."""
    monkeypatch.setattr(
        'api.routes.system._http_request',
        lambda *a, **k: (200, b"{}"),
    )
    resp = client.post('/api/system/check/api')

    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == {'service', 'ok', 'status', 'latency_ms', 'detail', 'error'}
    assert body['ok'] is True
    assert body['status'] == 'ok'
    assert isinstance(body['latency_ms'], int) and body['latency_ms'] >= 0
    assert body['error'] is None


def test_check_frontend_schema(monkeypatch):
    """POST /api/system/check/frontend -> 200 with the exact response schema."""
    monkeypatch.setattr(
        'api.routes.system._http_request',
        lambda *a, **k: (200, b"{}"),
    )
    resp = client.post('/api/system/check/frontend')

    assert resp.status_code == 200
    body = resp.json()

    assert body['ok'] is True
    assert body['status'] == 'ok'
