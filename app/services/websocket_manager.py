import asyncio
from collections import defaultdict

from fastapi import WebSocket

from app.utils.logger import logger


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)
        logger.info("ws_connected", user_id=user_id)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("ws_disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        sockets = self._connections.get(user_id, set()).copy()
        dead = set()
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        if dead:
            async with self._lock:
                self._connections[user_id] -= dead

    @property
    def connected_users(self) -> set[str]:
        return set(self._connections.keys())


ws_manager = WebSocketManager()
