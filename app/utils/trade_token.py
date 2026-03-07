"""
Signed trade confirmation tokens for email 'Proceed with Trade' links.

Tokens are short-lived JWTs (1 hour) that encode the trade parameters.
Redis tracks used tokens to prevent replay attacks.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
TOKEN_TTL_MINUTES = 60


def create_trade_token(
    user_id: str,
    ticker: str,
    action: str,
    shares: int,
    alert_id: str,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES)
    payload = {
        "type": "trade_confirm",
        "user_id": user_id,
        "ticker": ticker,
        "action": action,
        "shares": shares,
        "alert_id": alert_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_trade_token(token: str) -> dict:
    """Returns payload dict or raises JWTError."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "trade_confirm":
        raise JWTError("Not a trade confirmation token")
    return payload


def token_redis_key(token: str) -> str:
    """Stable Redis key derived from the token (avoids storing the full JWT as key)."""
    digest = hashlib.sha256(token.encode()).hexdigest()[:32]
    return f"trade_token_used:{digest}"
