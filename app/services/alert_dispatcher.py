import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert
from app.db.session import AsyncSessionLocal
from app.schemas.alert import ActionCard
from app.services.cache import publish
from app.services.websocket_manager import ws_manager
from app.utils.logger import logger


async def dispatch(action_card: ActionCard) -> None:
    """Persist alert to DB, publish to Redis, push via WebSocket for each target user."""
    async with AsyncSessionLocal() as db:
        for user_id in action_card.target_users:
            alert = Alert(
                id=uuid.UUID(action_card.alert_id) if len(action_card.target_users) == 1 else uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                ticker=action_card.ticker,
                alert_type="anomaly",
                payload=action_card.model_dump_json(),
                delivered_at=datetime.now(timezone.utc),
            )
            db.add(alert)

            payload_dict = action_card.model_dump()
            payload_dict["alert_db_id"] = str(alert.id)

            # Redis pub/sub for WebSocket bridge
            await publish(f"alerts:{user_id}", payload_dict)

            # Direct WebSocket push if connected
            await ws_manager.send_to_user(user_id, payload_dict)

        try:
            await db.commit()
        except Exception as e:
            logger.error("alert_dispatch_db_error", error=str(e))
            await db.rollback()
