"""
backtest/fixtures/_rate_limit.py — Rate limiter + 429 retry for Massive (Polygon) downloads.

Massive's free tier allows ~5 API calls per minute. The news/macro fixture
downloaders fire many requests back-to-back and previously died with
HTTP 429 after a few calls. This helper spaces calls by a minimum interval
(default 12s => 5/min) and retries 429 responses with exponential backoff.

Usage:
    limiter = RateLimiter()
    resp = get_with_retry(url, params, limiter=limiter)
"""

from __future__ import annotations

import time
from typing import Any, Callable

import requests

# Free tier: 5 calls/min → one call every 12s. Overridable for paid tiers.
DEFAULT_MIN_INTERVAL_SECONDS = 12.0
# Retry budget for 429 responses before giving up.
MAX_429_RETRIES = 5
# First backoff (seconds); doubles each attempt: 30s, 60s, 120s, ...
BACKOFF_BASE_SECONDS = 30.0


class RateLimiter:
    """Ensure at least ``min_interval`` seconds elapse between calls."""

    def __init__(self, min_interval: float = DEFAULT_MIN_INTERVAL_SECONDS) -> None:
        self.min_interval = min_interval
        self._last_call_at = 0.0

    def wait(self) -> None:
        """Block until the minimum interval since the previous call has passed."""
        now = time.monotonic()
        elapsed = now - self._last_call_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call_at = time.monotonic()


def get_with_retry(
    url: str,
    params: dict,
    limiter: RateLimiter | None = None,
    timeout: int = 30,
    _get: Callable[..., requests.Response] | None = None,
) -> requests.Response:
    """GET a URL with rate limiting and 429 backoff retry.

    Args:
        url: Request URL.
        params: Query params (e.g. {"apiKey": ...}).
        limiter: RateLimiter instance; defaults to a fresh one.
        timeout: Request timeout seconds.
        _get: Injectable HTTP GET (tests); defaults to requests.get.

    Returns:
        The 2xx response.

    Raises:
        requests.HTTPError: If the request fails with a non-429 status,
            or if 429 persists past MAX_429_RETRIES.
    """
    if limiter is None:
        limiter = RateLimiter()
    if _get is None:
        _get = requests.get

    for attempt in range(MAX_429_RETRIES):
        limiter.wait()
        resp = _get(url, params=params, timeout=timeout)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp

        # 429: respect Retry-After header when present, else exponential backoff
        retry_after = resp.headers.get("Retry-After") if hasattr(resp, "headers") else None
        try:
            wait = float(retry_after) if retry_after else BACKOFF_BASE_SECONDS * (2 ** attempt)
        except (TypeError, ValueError):
            wait = BACKOFF_BASE_SECONDS * (2 ** attempt)
        print(
            f"  [429] rate limited — retrying in {wait:.0f}s "
            f"(attempt {attempt + 1}/{MAX_429_RETRIES})",
            flush=True,
        )
        time.sleep(wait)

    raise requests.HTTPError(f"429 Too Many Requests after {MAX_429_RETRIES} retries: {url}")
