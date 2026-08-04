"""Stocks router - public endpoints for stock metadata."""

from fastapi import APIRouter, HTTPException, Query

from app.models.stock import Stock

router = APIRouter()

# TODO: Replace with actual database queries via Supabase client
# For now, return mock data for testing


@router.get("", response_model=dict)
async def list_stocks(
    query: str | None = Query(None, description="Search by ticker or company name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List available stocks with metadata."""
    # TODO: Query stocks table, filter by query, paginate
    mock_stocks = [
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

    if query:
        query_upper = query.upper()
        mock_stocks = [
            s for s in mock_stocks
            if query_upper in s.ticker or query.lower() in s.company_name.lower()
        ]

    total = len(mock_stocks)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "data": [s.model_dump() for s in mock_stocks[start:end]],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/{ticker}", response_model=Stock)
async def get_stock(ticker: str):
    """Get stock metadata by ticker."""
    # TODO: Query stocks table by ticker
    mock_stocks = {
        "NVDA": Stock(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            sector="Technology",
            industry="Semiconductors",
            market_cap=3_000_000_000_000,
            exchange="NASDAQ",
            is_active=True,
            last_price=125.50,
        ),
        "AAPL": Stock(
            ticker="AAPL",
            company_name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3_500_000_000_000,
            exchange="NASDAQ",
            is_active=True,
            last_price=195.20,
        ),
        "TSLA": Stock(
            ticker="TSLA",
            company_name="Tesla, Inc.",
            sector="Consumer Cyclical",
            industry="Auto Manufacturers",
            market_cap=800_000_000_000,
            exchange="NASDAQ",
            is_active=True,
            last_price=245.80,
        ),
    }

    stock = mock_stocks.get(ticker.upper())
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    return stock
