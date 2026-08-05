"""Tests for watchlist endpoints."""

import pytest

pytestmark = pytest.mark.usefixtures("auth_user")


def test_add_to_watchlist(client):
    """Add stock to watchlist."""
    response = client.post("/api/watchlist", json={"ticker": "NVDA"})
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "NVDA"
    assert "id" in data


def test_add_to_watchlist_with_notes(client):
    """Add stock to watchlist with notes."""
    response = client.post(
        "/api/watchlist",
        json={"ticker": "NVDA", "notes": "Swing trade setup"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["notes"] == "Swing trade setup"


def test_add_to_watchlist_duplicate(client):
    """Adding duplicate ticker returns 409."""
    client.post("/api/watchlist", json={"ticker": "NVDA"})
    response = client.post("/api/watchlist", json={"ticker": "NVDA"})
    assert response.status_code == 409


def test_list_watchlist(client):
    """List watchlist returns items."""
    client.post("/api/watchlist", json={"ticker": "NVDA"})

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0


def test_update_watchlist_item(client):
    """Update watchlist item notes."""
    create_response = client.post("/api/watchlist", json={"ticker": "NVDA"})
    item_id = create_response.json()["id"]

    response = client.patch(
        f"/api/watchlist/{item_id}",
        json={"notes": "Updated notes"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "Updated notes"


def test_update_watchlist_item_not_found(client):
    """Update non-existent watchlist item returns 404."""
    response = client.patch(
        "/api/watchlist/non-existent-id",
        json={"notes": "test"},
    )
    assert response.status_code == 404


def test_remove_from_watchlist(client):
    """Remove stock from watchlist."""
    create_response = client.post("/api/watchlist", json={"ticker": "NVDA"})
    item_id = create_response.json()["id"]

    response = client.delete(f"/api/watchlist/{item_id}")
    assert response.status_code == 204


def test_remove_from_watchlist_not_found(client):
    """Remove non-existent watchlist item returns 404."""
    response = client.delete("/api/watchlist/non-existent-id")
    assert response.status_code == 404
