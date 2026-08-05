"""Tests for the get_current_user dependency in app/core/auth.py."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.auth import get_current_user


def _credentials(token: str) -> SimpleNamespace:
    """Build a minimal HTTPAuthorizationCredentials stand-in."""
    return SimpleNamespace(credentials=token)


def test_missing_credentials_raises_401() -> None:
    """get_current_user(None) should raise 401 with 'Missing bearer token'."""
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(credentials=None)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Missing bearer token"


@patch("app.core.auth.get_supabase")
def test_invalid_token_raises_401(mock_get_supabase: MagicMock) -> None:
    """When get_user returns None, raise 401 with 'Invalid token'."""
    mock_client = MagicMock()
    mock_client.auth.get_user.return_value = None
    mock_get_supabase.return_value = mock_client

    with pytest.raises(HTTPException) as excinfo:
        get_current_user(credentials=_credentials("bogus-token"))

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid token"
    mock_client.auth.get_user.assert_called_once_with(jwt="bogus-token")


@patch("app.core.auth.get_supabase")
def test_valid_token_returns_user(mock_get_supabase: MagicMock) -> None:
    """A successful get_user response should return the authenticated user."""
    fake_user = SimpleNamespace(id="abc-123")
    mock_client = MagicMock()
    mock_client.auth.get_user.return_value = SimpleNamespace(user=fake_user)
    mock_get_supabase.return_value = mock_client

    result = get_current_user(credentials=_credentials("valid-token"))

    assert result is fake_user
    assert result.id == "abc-123"
    mock_client.auth.get_user.assert_called_once_with(jwt="valid-token")
