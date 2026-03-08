import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Alert, User
from app.db.session import AsyncSessionLocal
from app.schemas.alert import ActionCard
from app.services.cache import publish
from app.services.websocket_manager import ws_manager
from app.utils.logger import logger


async def dispatch(action_card: ActionCard) -> None:
    """Persist alert to DB, publish to Redis, push via WebSocket for each target user."""
    from app.services.cache import redis_client

    async with AsyncSessionLocal() as db:
        for user_id in action_card.target_users:
            # Dedup: skip if the exact same alert_id was dispatched in the last 15 seconds
            dedup_key = f"alert_dedup:{action_card.alert_id}:{user_id}"
            try:
                already_sent = await redis_client.set(dedup_key, "1", ex=15, nx=True)
                if not already_sent:
                    logger.info("alert_dedup_skip", ticker=action_card.ticker, user_id=user_id)
                    continue
            except Exception as e:
                logger.warning("alert_dedup_redis_error", error=str(e))

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

            # Auto-send alert email + trade draft (only if enabled)
            from app.config import settings
            if settings.auto_email_alerts:
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                user = result.scalar_one_or_none()
                if user:
                    asyncio.create_task(_send_alert_emails(action_card, user_id, user.email))

        try:
            await db.commit()
        except Exception as e:
            logger.error("alert_dispatch_db_error", error=str(e))
            await db.rollback()


async def _send_alert_emails(action_card: ActionCard, user_id: str, to_email: str) -> None:
    import base64

    from app.services.chart_capture import capture_tradingview_chart
    from app.services.email_sender import send_full_alert_email
    from app.services.nova_reasoning import analyze_chart
    from app.utils.trade_token import create_trade_token

    sentiment_label = (action_card.sentiment or {}).get("label", "neutral")
    trade_action = "buy" if sentiment_label == "positive" else "sell"

    trade_token = create_trade_token(
        user_id=user_id,
        ticker=action_card.ticker,
        action=trade_action,
        shares=1,
        alert_id=action_card.alert_id,
    )

    # Capture TradingView chart via Nova Act (headless browser)
    chart_b64 = ""
    chart_analysis = ""
    chart_png = await capture_tradingview_chart(action_card.ticker)
    if chart_png:
        chart_b64 = base64.b64encode(chart_png).decode()
        try:
            chart_analysis = await analyze_chart(action_card.ticker, chart_png)
            logger.info("chart_analysis_complete", ticker=action_card.ticker)
        except Exception as exc:
            logger.warning("chart_analysis_failed", ticker=action_card.ticker, error=str(exc))

    await send_full_alert_email(
        to_email=to_email,
        action_card=action_card,
        trade_action=trade_action,
        trade_token=trade_token,
        chart_b64=chart_b64,
        chart_analysis=chart_analysis,
    )
