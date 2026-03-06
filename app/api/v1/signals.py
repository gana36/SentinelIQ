import json

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/live")
async def get_live_signals(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """Returns the last N raw signals from Redis."""
    from app.services.cache import redis_client

    raw = await redis_client.lrange("signals:live", 0, limit - 1)
    signals = [json.loads(item) for item in raw]
    return {"signals": signals, "count": len(signals)}
