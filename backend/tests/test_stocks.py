"""Tests for stocks endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from app.models.stock import Stock

# Mock stock data for testing
MOCK_STOCKS = [
    Stock(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        sector="Technology",
        industry="Semiconductors",
        market_cap=3_000_000_000_000,
        exchange="NASDAQ",
        is_active=True,
        last_price=125.50,
    ),
    Stock(
        ticker="AAPL",
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        market_cap=3_500_000_000_000,
        exchange="NASDAQ",
        is_active=True,
        last_price=195.20,
    ),
    Stock(
        ticker="TSLA",
        company_name="Tesla, Inc.",
        sector="Consumer Cyclical",
        industry="Auto Manufacturers",
        market_cap=800_000_000_000,
        exchange="NASDAQ",
        is_active=True,
        last_price=245.80,
    ),
]


@pytest.fixture(autouse=True)
def mock_stock_repository():
    """Mock the stock repository for all tests."""
    with patch("app.routers.stocks._get_stock_repo") as mock_repo:
        mock_instance = MagicMock()
        mock_repo.return_value = mock_instance

        # Default list_stocks behavior
        def mock_list_stocks(query=None, page=1, page_size=20):
            stocks = MOCK_STOCKS
            if query:
                query_upper = query.upper()
                stocks = [
                    s for s in stocks
                    if query_upper in s.ticker or query.lower() in s.company_name.lower()
                ]
            total = len(stocks)
            start = (page - 1) * page_size
            end = start + page_size
            return stocks[start:end], total

        mock_instance.list_stocks.side_effect = mock_list_stocks

        # Default get_stock behavior
        def mock_get_stock(ticker):
            for stock in MOCK_STOCKS:
                if stock.ticker == ticker.upper():
                    return stock
            return None

        mock_instance.get_stock.side_effect = mock_get_stock

        yield mock_instance


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
