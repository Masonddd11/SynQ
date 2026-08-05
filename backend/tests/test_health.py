"""Tests for health endpoint."""


def test_health_check(client):
    """Health check returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
