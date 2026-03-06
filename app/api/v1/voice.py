import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.services.nova_sonic import explain

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceRequest(BaseModel):
    alert_id: uuid.UUID
    question: str = "What happened and why does it matter?"


@router.post("/explain")
async def voice_explain(
    body: VoiceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == body.alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    payload = json.loads(alert.payload)
    response = await explain(payload, body.question)
    return response
