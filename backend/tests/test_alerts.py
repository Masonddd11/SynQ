"""Tests for alerts endpoints."""


def test_create_alert(client):
    """Create alert rule."""
    response = client.post(
        "/api/alerts",
        json={"ticker": "NVDA", "alertType": "score_change", "threshold": 15},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "NVDA"
    assert data["alertType"] == "score_change"
    assert data["threshold"] == 15.0


def test_create_alert_price_target(client):
    """Create price target alert."""
    response = client.post(
        "/api/alerts",
        json={"ticker": "NVDA", "alertType": "price_target", "targetPrice": 150.0},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["targetPrice"] == 150.0


def test_create_alert_missing_type(client):
    """Create alert without alertType returns validation error."""
    response = client.post("/api/alerts", json={"ticker": "NVDA"})
    assert response.status_code == 422


def test_list_alerts(client):
    """List alerts returns items."""
    client.post(
        "/api/alerts",
        json={"ticker": "NVDA", "alertType": "score_change"},
    )

    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0


def test_list_alerts_by_ticker(client):
    """List alerts filters by ticker."""
    client.post(
        "/api/alerts",
        json={"ticker": "NVDA", "alertType": "score_change"},
    )
    client.post(
        "/api/alerts",
        json={"ticker": "AAPL", "alertType": "signal_change"},
    )

    response = client.get("/api/alerts?ticker=NVDA")
    assert response.status_code == 200
    data = response.json()
    assert all(a["ticker"] == "NVDA" for a in data["data"])


def test_update_alert(client):
    """Update alert threshold."""
    create_response = client.post(
        "/api/alerts",
        json={"ticker": "NVDA", "alertType": "score_change", "threshold": 10},
    )
    alert_id = create_response.json()["id"]

    response = client.patch(
        f"/api/alerts/{alert_id}",
        json={"threshold": 20},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["threshold"] == 20.0


def test_update_alert_deactivate(client):
    """Deactivate alert."""
    create_response = client.post(
        "/api/alerts",
        json={"ticker": "NVDA", "alertType": "score_change"},
    )
    alert_id = create_response.json()["id"]

    response = client.patch(
        f"/api/alerts/{alert_id}",
        json={"isActive": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["isActive"] is False


def test_delete_alert(client):
    """Delete alert rule."""
    create_response = client.post(
        "/api/alerts",
        json={"ticker": "NVDA", "alertType": "score_change"},
    )
    alert_id = create_response.json()["id"]

    response = client.delete(f"/api/alerts/{alert_id}")
    assert response.status_code == 204


def test_delete_alert_not_found(client):
    """Delete non-existent alert returns 404."""
    response = client.delete("/api/alerts/non-existent-id")
    assert response.status_code == 404
