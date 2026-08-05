"""Tests for analyses endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.models.analysis import Analysis, AnalysisStatus

# Matches VALID_USER.id injected by the auth_user fixture
TEST_USER_ID = "test-user-123"

pytestmark = pytest.mark.usefixtures("auth_user")


def _analysis(analysis_id: str, ticker: str, status: AnalysisStatus) -> Analysis:
    """Build an Analysis model instance the mocked repo will return."""
    now = datetime.now(UTC)
    completed_at = now if status == AnalysisStatus.COMPLETED else None
    return Analysis(
        id=analysis_id,
        ticker=ticker,
        status=status,
        created_at=now,
        completed_at=completed_at,
    )


@pytest.fixture(autouse=True)
def mock_analysis_repository(monkeypatch):
    """Patch dev_user_id and mock the analysis repository for all tests."""
    # 1. Patch settings.dev_user_id -> "test-user" (reset on teardown)
    monkeypatch.setattr(settings, "dev_user_id", TEST_USER_ID)

    # 2. Patch _get_analysis_repo to return a MagicMock
    with patch("app.routers.analyses._get_analysis_repo") as mock_repo:
        mock_instance = MagicMock()
        mock_repo.return_value = mock_instance

        # Shared in-memory "database" so calls behave consistently per test
        store: dict[str, Analysis] = {
            "a1": _analysis("a1", "NVDA", AnalysisStatus.PENDING),
            "a2": _analysis("a2", "NVDA", AnalysisStatus.COMPLETED),
            "a3": _analysis("a3", "AAPL", AnalysisStatus.PENDING),
        }

        # Default create_analysis behavior (overridden per-test where needed)
        def mock_create(owner_id, ticker):
            analysis_id = f"new-{ticker.lower()}"
            return _analysis(analysis_id, ticker.upper(), AnalysisStatus.PENDING)

        mock_instance.create_analysis.side_effect = mock_create

        # Default list_analyses behavior: filter store by ticker, paginate
        def mock_list(user_id, ticker=None, status=None, page=1, page_size=20):
            rows = list(store.values())
            if ticker:
                rows = [a for a in rows if a.ticker == ticker.upper()]
            if status:
                rows = [a for a in rows if a.status == status]
            total = len(rows)
            start = (page - 1) * page_size
            end = start + page_size
            return rows[start:end], total

        mock_instance.list_analyses.side_effect = mock_list

        # Default get_analysis behavior: look up by id in store
        def mock_get(owner_id, analysis_id):
            return store.get(analysis_id)

        mock_instance.get_analysis.side_effect = mock_get

        # Default get_latest_analysis behavior: newest COMPLETED analysis for ticker
        def mock_get_latest(owner_id, ticker):
            completed = [
                a
                for a in store.values()
                if a.ticker == ticker.upper() and a.status == AnalysisStatus.COMPLETED
            ]
            if not completed:
                return None
            completed.sort(key=lambda a: a.completed_at or datetime.min, reverse=True)
            return completed[0]

        mock_instance.get_latest_analysis.side_effect = mock_get_latest

        yield mock_instance


def test_create_analysis(client, mock_analysis_repository):
    """Create analysis returns pending status."""
    response = client.post("/api/analyses", json={"ticker": "NVDA"})
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "NVDA"
    assert data["status"] == "pending"
    assert "id" in data


def test_create_analysis_invalid_ticker(client, mock_analysis_repository):
    """Create analysis with empty ticker returns validation error (before repo)."""
    response = client.post("/api/analyses", json={"ticker": ""})
    assert response.status_code == 422
    # No repo interaction should happen on the 422 path
    mock_analysis_repository.create_analysis.assert_not_called()


def test_list_analyses(client, mock_analysis_repository):
    """List analyses returns paginated results."""
    response = client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0
    assert data["pagination"]["total_items"] == 3


def test_list_analyses_by_ticker(client, mock_analysis_repository):
    """List analyses filters by ticker."""
    response = client.get("/api/analyses?ticker=NVDA")
    assert response.status_code == 200
    data = response.json()
    assert all(a["ticker"] == "NVDA" for a in data["data"])


def test_get_analysis(client, mock_analysis_repository):
    """Get analysis by ID returns analysis data."""
    response = client.get("/api/analyses/a1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "a1"
    assert data["ticker"] == "NVDA"


def test_get_analysis_not_found(client, mock_analysis_repository):
    """Get analysis by non-existent ID returns 404."""
    mock_analysis_repository.get_analysis.return_value = None
    response = client.get("/api/analyses/non-existent-id")
    assert response.status_code == 404


def test_get_latest_analysis(client, mock_analysis_repository):
    """Get latest analysis for a ticker returns a completed analysis."""
    response = client.get("/api/analyses/latest?ticker=NVDA")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "NVDA"
    assert data["status"] == "completed"


def test_get_latest_analysis_not_found(client, mock_analysis_repository):
    """Get latest analysis for ticker with no completed analysis returns 404."""
    mock_analysis_repository.get_latest_analysis.return_value = None
    response = client.get("/api/analyses/latest?ticker=NONEXISTENT")
    assert response.status_code == 404


def test_owner_id_passed_to_create(client, mock_analysis_repository):
    """Router passes the authenticated user's id as owner to create_analysis."""
    client.post("/api/analyses", json={"ticker": "NVDA"})
    mock_analysis_repository.create_analysis.assert_called_with(TEST_USER_ID, "NVDA")
