"""Tests for stocks endpoints."""


def test_list_stocks(client):
    """List stocks returns paginated results."""
    response = client.get("/api/stocks")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0
    assert data["pagination"]["total_items"] > 0


def test_list_stocks_with_query(client):
    """List stocks filters by query."""
    response = client.get("/api/stocks?query=NVDA")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["ticker"] == "NVDA"


def test_list_stocks_pagination(client):
    """List stocks respects pagination."""
    response = client.get("/api/stocks?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 2


def test_get_stock(client):
    """Get stock by ticker returns stock data."""
    response = client.get("/api/stocks/NVDA")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "NVDA"
    assert data["companyName"] == "NVIDIA Corporation"


def test_get_stock_not_found(client):
    """Get stock by non-existent ticker returns 404."""
    response = client.get("/api/stocks/INVALID")
    assert response.status_code == 404


def test_get_stock_case_insensitive(client):
    """Get stock works with lowercase ticker."""
    response = client.get("/api/stocks/nvda")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "NVDA"
