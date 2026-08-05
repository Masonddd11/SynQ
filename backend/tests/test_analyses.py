"""Tests for analyses endpoints."""


def test_create_analysis(client):
    """Create analysis returns pending status."""
    response = client.post("/api/analyses", json={"ticker": "NVDA"})
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "NVDA"
    assert data["status"] == "pending"
    assert "id" in data


def test_create_analysis_invalid_ticker(client):
    """Create analysis with empty ticker returns validation error."""
    response = client.post("/api/analyses", json={"ticker": ""})
    assert response.status_code == 422


def test_list_analyses(client):
    """List analyses returns paginated results."""
    # Create an analysis first
    client.post("/api/analyses", json={"ticker": "NVDA"})

    response = client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0


def test_list_analyses_by_ticker(client):
    """List analyses filters by ticker."""
    client.post("/api/analyses", json={"ticker": "NVDA"})
    client.post("/api/analyses", json={"ticker": "AAPL"})

    response = client.get("/api/analyses?ticker=NVDA")
    assert response.status_code == 200
    data = response.json()
    assert all(a["ticker"] == "NVDA" for a in data["data"])


def test_get_analysis(client):
    """Get analysis by ID returns analysis data."""
    create_response = client.post("/api/analyses", json={"ticker": "NVDA"})
    analysis_id = create_response.json()["id"]

    response = client.get(f"/api/analyses/{analysis_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analysis_id
    assert data["ticker"] == "NVDA"


def test_get_analysis_not_found(client):
    """Get analysis by non-existent ID returns 404."""
    response = client.get("/api/analyses/non-existent-id")
    assert response.status_code == 404


def test_get_latest_analysis(client):
    """Get latest analysis for a ticker."""
    client.post("/api/analyses", json={"ticker": "NVDA"})

    response = client.get("/api/analyses/latest?ticker=NVDA")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "NVDA"
    assert data["status"] == "completed"


def test_get_latest_analysis_not_found(client):
    """Get latest analysis for ticker with no analyses returns 404."""
    response = client.get("/api/analyses/latest?ticker=NONEXISTENT")
    assert response.status_code == 404
