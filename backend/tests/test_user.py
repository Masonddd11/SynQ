"""Tests for user endpoints."""


def test_get_profile(client):
    """Get user profile."""
    response = client.get("/api/user/profile")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert data["subscriptionTier"] == "free"


def test_update_profile(client):
    """Update user profile."""
    response = client.patch(
        "/api/user/profile",
        params={"full_name": "New Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fullName"] == "New Name"


def test_get_subscription(client):
    """Get subscription status."""
    response = client.get("/api/user/subscription")
    assert response.status_code == 200
    data = response.json()
    assert "tier" in data
    assert "analysesUsedToday" in data
    assert "dailyLimit" in data
    assert "resetsAt" in data
