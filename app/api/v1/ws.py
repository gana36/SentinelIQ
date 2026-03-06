import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.security import decode_token
from app.services.cache import get_subscriber
from app.services.websocket_manager import ws_manager
from app.utils.logger import logger

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket, token: str = Query(...)):
    # Authenticate
    try:
        user_id = decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return

    await ws_manager.connect(user_id, websocket)
    pubsub = await get_subscriber()
    await pubsub.subscribe(f"alerts:{user_id}")

    try:
        # Concurrently handle: incoming pings + Redis pub/sub messages
        async def _redis_listener():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await ws_manager.send_to_user(user_id, {"raw": message["data"]})

        listener_task = asyncio.create_task(_redis_listener())

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except (WebSocketDisconnect, Exception) as e:
        logger.info("ws_client_disconnected", user_id=user_id, reason=str(e))
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe(f"alerts:{user_id}")
        await pubsub.aclose()
        await ws_manager.disconnect(user_id, websocket)
