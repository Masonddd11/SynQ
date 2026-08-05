"""Test configuration and fixtures."""

from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.routers.watchlist import clear_watchlist_db

VALID_USER = SimpleNamespace(id="test-user-123", email="test@example.com")


@pytest.fixture(autouse=True)
def clear_state():
    """Clear in-memory state between tests."""
    clear_watchlist_db()
    yield


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_ticker():
    """Sample ticker for testing."""
    return "NVDA"


@pytest.fixture
def auth_user() -> Iterator[SimpleNamespace]:
    """Override the get_current_user dependency to return VALID_USER.

    Uses FastAPI's ``app.dependency_overrides`` (not module-attribute
    monkeypatching — routes capture the original dependency function object at
    decoration time, so patching ``app.routers.<mod>.get_current_user`` would
    not affect already-registered routes).

    Valid-path tests opt in by requesting this fixture (e.g. via
    ``@pytest.mark.usefixtures("auth_user")``). Tests that exercise the real
    401 behavior (test_auth_required.py) deliberately do NOT request it.
    """
    app.dependency_overrides[get_current_user] = lambda: VALID_USER
    yield VALID_USER
    app.dependency_overrides.pop(get_current_user, None)
