import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.alert import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _parse_alert(alert: Alert) -> AlertOut:
    return AlertOut(
        id=alert.id,
        ticker=alert.ticker,
        alert_type=alert.alert_type,
        payload=json.loads(alert.payload),
        created_at=alert.created_at,
        delivered_at=alert.delivered_at,
        read_at=alert.read_at,
    )


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert)
        .where(Alert.user_id == current_user.id)
        .order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [_parse_alert(a) for a in result.scalars().all()]


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _parse_alert(alert)


@router.patch("/{alert_id}/read", response_model=AlertOut)
async def mark_read(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not alert.read_at:
        alert.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(alert)
    return _parse_alert(alert)
