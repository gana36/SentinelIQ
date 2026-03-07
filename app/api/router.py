from fastapi import APIRouter

from app.api.v1 import auth, users, watchlist, alerts, signals, market, voice, ws, dev, trade

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(watchlist.router)
api_router.include_router(alerts.router)
api_router.include_router(signals.router)
api_router.include_router(market.router)
api_router.include_router(voice.router)
api_router.include_router(ws.router)
api_router.include_router(dev.router)
api_router.include_router(trade.router)
