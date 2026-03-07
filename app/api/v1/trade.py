import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from jose import JWTError
from pydantic import BaseModel

from app.db.models import User
from app.dependencies import get_current_user
from app.services.nova_act_trader import draft_trade, execute_trade
from app.services.email_sender import send_trade_draft_email, send_trade_confirmation_email

router = APIRouter(prefix="/trade", tags=["trade"])


class DraftRequest(BaseModel):
    ticker: str
    action: str = "buy"   # "buy" | "sell"
    shares: int = 1
    est_price: float = 0.0


class DraftResponse(BaseModel):
    session_id: str
    ticker: str
    action: str
    shares: int
    est_price: float
    est_total: float
    screenshot_b64: str
    screenshot_mime: str   # "image/png" or "image/svg+xml"
    is_mock: bool


@router.post("/draft", response_model=DraftResponse)
async def draft_trade_endpoint(
    body: DraftRequest,
    current_user: User = Depends(get_current_user),
):
    if body.shares < 1:
        raise HTTPException(status_code=400, detail="shares must be >= 1")
    if body.action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="action must be 'buy' or 'sell'")

    result = await draft_trade(
        ticker=body.ticker.upper(),
        action=body.action,
        shares=body.shares,
        est_price=body.est_price,
    )

    # Send screenshot to user's email in the background (non-blocking)
    asyncio.create_task(send_trade_draft_email(
        to_email=current_user.email,
        ticker=result.ticker,
        action=result.action,
        shares=result.shares,
        est_price=result.est_price,
        est_total=result.est_total,
        screenshot_b64=result.screenshot_b64,
        is_mock=result.is_mock,
    ))

    return DraftResponse(
        session_id=result.session_id,
        ticker=result.ticker,
        action=result.action,
        shares=result.shares,
        est_price=result.est_price,
        est_total=result.est_total,
        screenshot_b64=result.screenshot_b64,
        screenshot_mime="image/svg+xml",
        is_mock=result.is_mock,
    )


@router.post("/execute", response_model=DraftResponse)
async def execute_trade_endpoint(
    body: DraftRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute a trade via Nova Act (fills form AND clicks confirm on Alpaca)."""
    if body.shares < 1:
        raise HTTPException(status_code=400, detail="shares must be >= 1")
    if body.action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="action must be 'buy' or 'sell'")

    result = await execute_trade(
        ticker=body.ticker.upper(),
        action=body.action,
        shares=body.shares,
        est_price=body.est_price,
    )

    # Send confirmation email in background
    asyncio.create_task(send_trade_confirmation_email(
        to_email=current_user.email,
        ticker=result.ticker,
        action=result.action,
        shares=result.shares,
        screenshot_b64=result.screenshot_b64,
        is_mock=result.is_mock,
        est_price=result.est_price,
        est_total=result.est_total,
        order_id=result.session_id,
    ))

    return DraftResponse(
        session_id=result.session_id,
        ticker=result.ticker,
        action=result.action,
        shares=result.shares,
        est_price=result.est_price,
        est_total=result.est_total,
        screenshot_b64=result.screenshot_b64,
        screenshot_mime="image/svg+xml",
        is_mock=result.is_mock,
    )


@router.get("/confirm", response_class=HTMLResponse)
async def confirm_trade_endpoint(token: str):
    """
    Called when user clicks 'Proceed with Trade' in their alert email.
    Validates the signed token, executes the trade via Nova Act, sends confirmation email.
    """
    from app.utils.trade_token import decode_trade_token, token_redis_key
    from app.services.cache import redis_client
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select

    # --- Validate token ---
    try:
        payload = decode_trade_token(token)
    except JWTError:
        return HTMLResponse(_html_page(
            "Invalid or Expired Link",
            "This trade confirmation link is invalid or has expired (links expire after 1 hour).",
            success=False,
        ), status_code=400)

    user_id = payload["user_id"]
    ticker = payload["ticker"]
    action = payload["action"]
    shares = payload["shares"]

    # --- One-time use check ---
    redis_key = token_redis_key(token)
    already_used = await redis_client.get(redis_key)
    if already_used:
        return HTMLResponse(_html_page(
            "Already Used",
            "This trade confirmation link has already been used. Each link can only be used once.",
            success=False,
        ), status_code=409)

    # Mark token as used (TTL = 1 hour)
    await redis_client.set(redis_key, "1", ex=3600)

    # --- Execute trade via Nova Act ---
    result = await execute_trade(ticker=ticker, action=action, shares=shares, est_price=0.0)

    # --- Send confirmation email ---
    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = user_result.scalar_one_or_none()
        if user:
            asyncio.create_task(send_trade_confirmation_email(
                to_email=user.email,
                ticker=ticker,
                action=action,
                shares=shares,
                screenshot_b64=result.screenshot_b64,
                is_mock=result.is_mock,
                est_price=result.est_price,
                est_total=result.est_total,
                order_id=result.session_id,
            ))

    return HTMLResponse(_html_page(
        f"Trade Submitted — {action.upper()} {ticker}",
        f"Nova Act has placed your paper trade: {action.upper()} {shares} share{'s' if shares != 1 else ''} of {ticker} on Alpaca. A confirmation email is on its way.",
        success=True,
        ticker=ticker,
        action=action,
    ))


def _html_page(title: str, message: str, success: bool, ticker: str = "", action: str = "") -> str:
    color = "#10B981" if success else "#EF4444"
    icon = "&#10003;" if success else "&#10005;"
    action_color = "#10B981" if action == "buy" else "#EF4444" if action else color
    badge = f"<div class='badge'>{action.upper()} {ticker}</div>" if ticker else ""
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>SentinelIQ &mdash; {title}</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; background: #0f1117; color: #e2e8f0;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
    .card {{ background: #1e2130; border-radius: 16px; padding: 48px 40px; max-width: 440px;
             width: 100%; text-align: center; box-shadow: 0 4px 32px rgba(0,0,0,0.4); }}
    .icon {{ width: 64px; height: 64px; border-radius: 50%; background: {color}22;
             display: flex; align-items: center; justify-content: center;
             font-size: 28px; color: {color}; margin: 0 auto 24px; line-height: 64px; }}
    h1 {{ font-size: 20px; font-weight: 700; margin: 0 0 12px; color: white; }}
    p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 16px; }}
    .badge {{ display: inline-block; background: {action_color}22; color: {action_color};
              padding: 4px 14px; border-radius: 6px; font-size: 13px; font-weight: 600;
              margin-bottom: 20px; }}
    .brand {{ color: #475569; font-size: 12px; margin-top: 24px; }}
    .brand span {{ color: #10B981; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    {badge}
    <h1>{title}</h1>
    <p>{message}</p>
    <p class="brand">Powered by <span>SentinelIQ</span> &middot; Amazon Nova</p>
  </div>
</body>
</html>"""
