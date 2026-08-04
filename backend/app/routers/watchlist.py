"""Watchlist router - manage tracked stocks."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.models.watchlist import (
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
    WatchlistItem,
)

router = APIRouter()

# TODO: Replace with actual database queries via Supabase client
# For now, use in-memory storage for testing

_watchlist_db: dict[str, WatchlistItem] = {}


@router.get("", response_model=dict)
async def list_watchlist(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List user's watchlist."""
    # TODO: Query watchlist table filtered by user_id
    items = list(_watchlist_db.values())

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "data": [item.model_dump() for item in items[start:end]],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(request: CreateWatchlistRequest):
    """Add a stock to watchlist."""
    # TODO: Check if ticker exists in stocks table
    # TODO: Check if already in user's watchlist (return 409)
    # TODO: Verify user is authenticated

    ticker = request.ticker.upper()

    # Check for duplicates
    for item in _watchlist_db.values():
        if item.ticker == ticker:
            raise HTTPException(status_code=409, detail="Ticker already in watchlist")

    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    item = WatchlistItem(
        id=item_id,
        ticker=ticker,
        notes=request.notes,
        alert_threshold=request.alert_threshold,
        created_at=now,
        updated_at=now,
    )

    _watchlist_db[item_id] = item
    return item


@router.patch("/{item_id}", response_model=WatchlistItem)
async def update_watchlist_item(item_id: str, request: UpdateWatchlistRequest):
    """Update watchlist item."""
    # TODO: Verify user owns this item
    item = _watchlist_db.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    if request.notes is not None:
        item.notes = request.notes
    if request.alert_threshold is not None:
        item.alert_threshold = request.alert_threshold

    item.updated_at = datetime.now(timezone.utc)
    return item


@router.delete("/{item_id}", status_code=204)
async def remove_from_watchlist(item_id: str):
    """Remove stock from watchlist."""
    # TODO: Verify user owns this item
    if item_id not in _watchlist_db:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    del _watchlist_db[item_id]
