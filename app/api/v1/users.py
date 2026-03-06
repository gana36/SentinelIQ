import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserPreferences
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.user import PreferencesOut, PreferencesUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/preferences", response_model=PreferencesOut)
async def get_preferences(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == current_user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        return PreferencesOut(risk_tolerance="medium", alert_sensitivity=0.5, sectors=[])
    return PreferencesOut(
        risk_tolerance=prefs.risk_tolerance,
        alert_sensitivity=prefs.alert_sensitivity,
        sectors=json.loads(prefs.sectors),
    )


@router.patch("/me/preferences", response_model=PreferencesOut)
async def update_preferences(
    body: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == current_user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id, sectors=json.dumps([]))
        db.add(prefs)

    if body.risk_tolerance is not None:
        prefs.risk_tolerance = body.risk_tolerance
    if body.alert_sensitivity is not None:
        prefs.alert_sensitivity = body.alert_sensitivity
    if body.sectors is not None:
        prefs.sectors = json.dumps(body.sectors)

    await db.commit()
    await db.refresh(prefs)
    return PreferencesOut(
        risk_tolerance=prefs.risk_tolerance,
        alert_sensitivity=prefs.alert_sensitivity,
        sectors=json.loads(prefs.sectors),
    )
