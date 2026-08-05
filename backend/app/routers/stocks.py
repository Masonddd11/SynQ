"""Stocks router - public endpoints for stock metadata."""

from fastapi import APIRouter, HTTPException, Query

from app.models.stock import Stock
from app.repositories.stock import StockRepository

router = APIRouter()

# Lazy-initialized repository instance
_stock_repo: StockRepository | None = None


def _get_stock_repo() -> StockRepository:
    """Get or create the stock repository instance."""
    global _stock_repo
    if _stock_repo is None:
        _stock_repo = StockRepository()
    return _stock_repo


@router.get("", response_model=dict)
async def list_stocks(
    query: str | None = Query(None, description="Search by ticker or company name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List available stocks with metadata."""
    try:
        repo = _get_stock_repo()
        stocks, total = repo.list_stocks(query=query, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "data": [s.model_dump() for s in stocks],
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
    try:
        repo = _get_stock_repo()
        stock = repo.get_stock(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    return stock
