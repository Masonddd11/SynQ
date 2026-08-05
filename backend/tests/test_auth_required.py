"""Tests that every protected endpoint returns 401 without valid auth.

This module intentionally does NOT use the ``auth_user`` override fixture: it
exercises the REAL ``get_current_user`` dependency (``app.core.auth``) so we
prove the hard-401 guard is actually wired into every router.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# (method, path) for every protected endpoint across the guarded routers.
# POST cases carry no body: the auth dependency resolves and fails before body
# validation, so an empty request still yields 401.
_PROTECTED_ENDPOINTS: list[tuple[str, str]] = [
    # analyses
    ("GET", "/api/analyses"),
    ("POST", "/api/analyses"),
    ("GET", "/api/analyses/latest?ticker=NVDA"),
    # watchlist
    ("GET", "/api/watchlist"),
    ("POST", "/api/watchlist"),
    # alerts
    ("GET", "/api/alerts"),
    ("POST", "/api/alerts"),
    # user
    ("GET", "/api/user/profile"),
    ("GET", "/api/user/subscription"),
]


@pytest.fixture
def reject_invalid_tokens() -> Iterator[None]:
    """Let the real get_current_user run; make get_user return None -> 401."""
    mock_client = MagicMock()
    mock_client.auth.get_user.return_value = None
    with patch("app.core.auth.get_supabase", return_value=mock_client):
        yield


def _assert_401(
    client: TestClient, method: str, url: str, headers: dict[str, str] | None
) -> None:
    resp = client.request(method, url, headers=headers)
    assert resp.status_code == 401


@pytest.mark.parametrize("method,url", _PROTECTED_ENDPOINTS)
def test_no_authorization_header_returns_401(
    client: TestClient, method: str, url: str
) -> None:
    """No Authorization header -> HTTPBearer(auto_error=False) -> 401."""
    _assert_401(client, method, url, headers=None)


@pytest.mark.parametrize("method,url", _PROTECTED_ENDPOINTS)
def test_invalid_token_returns_401(
    client: TestClient, reject_invalid_tokens: None, method: str, url: str
) -> None:
    """Bearer bogus-token -> get_user returns None -> 401 'Invalid token'."""
    _assert_401(client, method, url, headers={"Authorization": "Bearer bogus-token"})
