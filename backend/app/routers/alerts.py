"""Alerts router - manage notification rules."""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase_auth.types import User

from app.core.auth import get_current_user
from app.models.alert import Alert, CreateAlertRequest, UpdateAlertRequest

router = APIRouter()

_alerts_db: dict[str, Alert] = {}


@router.get("", response_model=dict)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ticker: str | None = Query(None),
    is_active: bool | None = Query(None),
    user: User = Depends(get_current_user),
):
    alerts = list(_alerts_db.values())
    if ticker:
        alerts = [a for a in alerts if a.ticker == ticker.upper()]
    if is_active is not None:
        alerts = [a for a in alerts if a.is_active == is_active]
    total = len(alerts)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "data": [alert.model_dump() for alert in alerts[start:end]],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("", response_model=Alert, status_code=201)
async def create_alert(
    request: CreateAlertRequest,
    user: User = Depends(get_current_user),
):
    ticker = request.ticker.upper()
    alert_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    alert = Alert(
        id=alert_id,
        ticker=ticker,
        alert_type=request.alert_type,
        threshold=request.threshold,
        target_price=request.target_price,
        is_active=True,
        created_at=now,
    )
    _alerts_db[alert_id] = alert
    return alert


@router.patch("/{alert_id}", response_model=Alert)
async def update_alert(
    alert_id: str,
    request: UpdateAlertRequest,
    user: User = Depends(get_current_user),
):
    alert = _alerts_db.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if request.threshold is not None:
        alert.threshold = request.threshold
    if request.target_price is not None:
        alert.target_price = request.target_price
    if request.is_active is not None:
        alert.is_active = request.is_active
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    user: User = Depends(get_current_user),
):
    if alert_id not in _alerts_db:
        raise HTTPException(status_code=404, detail="Alert not found")
    del _alerts_db[alert_id]
