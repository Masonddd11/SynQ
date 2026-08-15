"""
tests/test_fixture_rate_limit.py — Unit tests for the Massive/Polygon
fixture-download rate limiter + 429 retry helper.

Regression: refresh_news.py fired API calls ~5/sec against the free-tier
5 calls/min limit and died with HTTP 429 on the 6th day. The helper must
space calls by a minimum interval and retry 429 responses with backoff.
"""

from __future__ import annotations

import time

import pytest

from backtest.fixtures._rate_limit import RateLimiter, get_with_retry


def test_rate_limiter_enforces_minimum_interval():
    """S1: consecutive waits must be >= min_interval apart."""
    limiter = RateLimiter(min_interval=0.05)
    limiter.wait()
    start = time.monotonic()
    limiter.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.04  # allow tiny clock tolerance


def test_get_with_retry_success_first_try():
    """S2: a 2xx response is returned without retry."""
    calls = []

    class _FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"results": []}

    def fake_get(url, params=None, timeout=30):
        calls.append(url)
        return _FakeResp()

    resp = get_with_retry("https://api.massive.com/v2/reference/news", {"apiKey": "k"},
                          limiter=RateLimiter(min_interval=0.0), _get=fake_get)
    assert len(calls) == 1
    assert resp.status_code == 200


def test_get_with_retry_429_backoff_then_success(monkeypatch):
    """S3: 429 responses retry after backoff and eventually succeed."""
    from backtest.fixtures import _rate_limit as rl

    statuses = [429, 429, 200]
    calls = {"n": 0}

    class _FakeResp:
        def __init__(self, status_code):
            self.status_code = status_code
            self.headers = {}

        def raise_for_status(self):
            if self.status_code >= 400:
                import requests
                raise requests.HTTPError(f"{self.status_code} Client Error")

    def fake_get(url, params=None, timeout=30):
        calls["n"] += 1
        return _FakeResp(statuses[calls["n"] - 1])

    monkeypatch.setattr(rl, "BACKOFF_BASE_SECONDS", 0.01)
    resp = get_with_retry("https://api.massive.com/v2/reference/news", {"apiKey": "k"},
                          limiter=RateLimiter(min_interval=0.0), _get=fake_get)
    assert calls["n"] == 3
    assert resp.status_code == 200


def test_get_with_retry_raises_after_max_retries(monkeypatch):
    """S4: persistent 429 raises after the retry budget is exhausted."""
    from backtest.fixtures import _rate_limit as rl

    class _FakeResp:
        status_code = 429
        headers = {}

        def raise_for_status(self):
            import requests
            raise requests.HTTPError("429 Too Many Requests")

    def fake_get(url, params=None, timeout=30):
        return _FakeResp()

    monkeypatch.setattr(rl, "BACKOFF_BASE_SECONDS", 0.01)
    with pytest.raises(Exception):
        get_with_retry("https://api.massive.com/v2/reference/news", {"apiKey": "k"},
                       limiter=RateLimiter(min_interval=0.0), _get=fake_get)
