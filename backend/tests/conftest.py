"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.watchlist import clear_watchlist_db


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
