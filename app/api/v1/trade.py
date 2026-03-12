import asyncio
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException
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


class ExecuteRequest(DraftRequest):
    alpaca_key: str = ""
    alpaca_secret: str = ""


class ConfirmJsonRequest(BaseModel):
    token: str
    action: str = "buy"
    shares: int = 1
    alpaca_key: str = ""
    alpaca_secret: str = ""


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
    body: ExecuteRequest,
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
        alpaca_key=body.alpaca_key,
        alpaca_secret=body.alpaca_secret,
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


@router.get("/token-info")
async def trade_token_info(token: str):
    """Decode a trade token and return its payload (no auth, no consumption)."""
    from app.utils.trade_token import decode_trade_token, token_redis_key
    from app.services.cache import redis_client

    try:
        payload = decode_trade_token(token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired trade token")

    already_used = await redis_client.get(token_redis_key(token))
    if already_used:
        raise HTTPException(status_code=409, detail="Trade link already used")

    return {
        "ticker": payload["ticker"],
        "action": payload["action"],
        "shares": payload["shares"],
    }


@router.post("/confirm-json")
async def confirm_trade_json(body: ConfirmJsonRequest):
    """Execute a trade from an email token — returns JSON (used by React confirm page)."""
    from app.utils.trade_token import decode_trade_token, token_redis_key
    from app.services.cache import redis_client
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select

    try:
        payload = decode_trade_token(body.token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired trade token")

    redis_key = token_redis_key(body.token)
    already_used = await redis_client.get(redis_key)
    if already_used:
        raise HTTPException(status_code=409, detail="Trade link already used")

    await redis_client.set(redis_key, "1", ex=3600)

    ticker = payload["ticker"]
    user_id = payload["user_id"]
    shares = max(1, body.shares)
    action = body.action if body.action in ("buy", "sell") else "buy"

    result = await execute_trade(
        ticker=ticker, action=action, shares=shares, est_price=0.0,
        alpaca_key=body.alpaca_key, alpaca_secret=body.alpaca_secret,
    )

    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = user_result.scalar_one_or_none()
        if user:
            asyncio.create_task(send_trade_confirmation_email(
                to_email=user.email,
                ticker=ticker, action=action, shares=shares,
                screenshot_b64=result.screenshot_b64, is_mock=result.is_mock,
                est_price=result.est_price, est_total=result.est_total,
                order_id=result.session_id,
            ))

    return DraftResponse(
        session_id=result.session_id, ticker=result.ticker, action=result.action,
        shares=result.shares, est_price=result.est_price, est_total=result.est_total,
        screenshot_b64=result.screenshot_b64, screenshot_mime="image/svg+xml",
        is_mock=result.is_mock,
    )


@router.get("/confirm", response_class=HTMLResponse)
async def confirm_trade_review(token: str):
    """
    Step 1 (GET): Called when user clicks email link.
    Shows order review page — user can adjust shares/action before confirming.
    Token is NOT consumed here.
    """
    from app.utils.trade_token import decode_trade_token, token_redis_key
    from app.services.cache import redis_client

    try:
        payload = decode_trade_token(token)
    except JWTError:
        return HTMLResponse(_html_page(
            "Invalid or Expired Link",
            "This trade confirmation link is invalid or has expired (links expire after 1 hour).",
            success=False,
        ), status_code=400)

    redis_key = token_redis_key(token)
    already_used = await redis_client.get(redis_key)
    if already_used:
        return HTMLResponse(_html_page(
            "Already Used",
            "This trade confirmation link has already been used. Each link can only be used once.",
            success=False,
        ), status_code=409)

    ticker = payload["ticker"]
    action = payload["action"]
    shares = payload["shares"]

    return HTMLResponse(_order_review_page(token=token, ticker=ticker, action=action, shares=shares))


@router.post("/confirm", response_class=HTMLResponse)
async def confirm_trade_execute(
    token: str,
    action: str = Form("buy"),
    shares: int = Form(1),
    alpaca_key: str = Form(""),
    alpaca_secret: str = Form(""),
):
    """
    Step 2 (POST): User submits the review form with (possibly adjusted) action/shares.
    Validates + consumes token, executes trade, sends confirmation email.
    """
    from app.utils.trade_token import decode_trade_token, token_redis_key
    from app.services.cache import redis_client
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select

    try:
        payload = decode_trade_token(token)
    except JWTError:
        return HTMLResponse(_html_page(
            "Invalid or Expired Link",
            "This trade confirmation link is invalid or has expired.",
            success=False,
        ), status_code=400)

    redis_key = token_redis_key(token)
    already_used = await redis_client.get(redis_key)
    if already_used:
        return HTMLResponse(_html_page(
            "Already Used",
            "This trade confirmation link has already been used.",
            success=False,
        ), status_code=409)

    # Consume the token
    await redis_client.set(redis_key, "1", ex=3600)

    ticker = payload["ticker"]
    user_id = payload["user_id"]
    shares = max(1, shares)
    action = action if action in ("buy", "sell") else "buy"

    result = await execute_trade(
        ticker=ticker, action=action, shares=shares, est_price=0.0,
        alpaca_key=alpaca_key, alpaca_secret=alpaca_secret,
    )

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


def _order_review_page(token: str, ticker: str, action: str, shares: int) -> str:
    action_color = "#10B981" if action == "buy" else "#EF4444"
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>SentinelIQ &mdash; Review Trade</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Inter, system-ui, sans-serif; background: #f8fafc; color: #0f172a;
           display: flex; flex-direction: column; align-items: center; justify-content: center;
           min-height: 100vh; }}
    .topbar {{ position: fixed; top: 0; left: 0; right: 0; height: 56px; background: white;
               border-bottom: 1px solid #e2e8f0; display: flex; align-items: center;
               padding: 0 24px; gap: 8px; }}
    .topbar-dot {{ width: 6px; height: 6px; border-radius: 50%; background: #10B981; margin-right: 2px; }}
    .topbar-logo {{ font-size: 15px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px; }}
    .topbar-sub {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 500; }}
    .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px;
             padding: 40px 36px; max-width: 420px; width: 100%; margin: 0 16px;
             box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04); }}
    h2 {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 4px; }}
    .sub {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 500; margin-bottom: 28px; }}
    label {{ display: block; font-size: 10px; font-weight: 700; text-transform: uppercase;
             letter-spacing: 0.1em; color: #94a3b8; margin-bottom: 8px; }}
    .toggle {{ display: flex; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 20px; }}
    .toggle input[type=radio] {{ display: none; }}
    .toggle label {{ flex: 1; text-align: center; padding: 10px; font-size: 13px; font-weight: 700;
                     text-transform: uppercase; letter-spacing: 0.08em; cursor: pointer;
                     color: #64748b; background: white; margin: 0; transition: all 0.15s; }}
    #buy:checked ~ .toggle-labels .buy-label {{ background: #10B981; color: white; }}
    #sell:checked ~ .toggle-labels .sell-label {{ background: #EF4444; color: white; }}
    .shares-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 28px; }}
    .shares-btn {{ width: 36px; height: 36px; border: 1px solid #e2e8f0; border-radius: 8px;
                   background: white; font-size: 18px; font-weight: 700; color: #475569;
                   cursor: pointer; display: flex; align-items: center; justify-content: center; }}
    .shares-btn:hover {{ border-color: #94a3b8; color: #0f172a; }}
    .shares-input {{ flex: 1; text-align: center; font-size: 18px; font-weight: 700;
                     color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px;
                     padding: 8px; outline: none; }}
    .shares-input:focus {{ border-color: #94a3b8; }}
    .submit-btn {{ width: 100%; padding: 13px; border: none; border-radius: 8px;
                   font-size: 13px; font-weight: 700; text-transform: uppercase;
                   letter-spacing: 0.08em; cursor: pointer; color: white;
                   background: {action_color}; transition: opacity 0.15s; }}
    .submit-btn:hover {{ opacity: 0.9; }}
    .disclaimer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 14px; }}
    .brand {{ font-size: 11px; color: #cbd5e1; text-align: center; margin-top: 20px; }}
    .brand span {{ color: #10B981; font-weight: 600; }}
    .advanced-toggle {{ font-size: 11px; color: #94a3b8; cursor: pointer; background: none;
                        border: none; padding: 0; margin-bottom: 16px; display: flex;
                        align-items: center; gap: 4px; font-weight: 600; letter-spacing: 0.05em; }}
    .advanced-toggle:hover {{ color: #64748b; }}
    .advanced-section {{ display: none; border: 1px solid #e2e8f0; border-radius: 8px;
                          padding: 16px; margin-bottom: 20px; background: #f8fafc; }}
    .advanced-section.open {{ display: block; }}
    .api-input {{ width: 100%; font-size: 13px; color: #0f172a; border: 1px solid #e2e8f0;
                  border-radius: 6px; padding: 8px 10px; outline: none; background: white;
                  font-family: monospace; margin-bottom: 10px; }}
    .api-input:focus {{ border-color: #94a3b8; }}
    .api-hint {{ font-size: 11px; color: #94a3b8; margin-bottom: 0; }}
  </style>
  <script>
    function toggleAdvanced() {{
      var s = document.getElementById('advanced-section');
      s.classList.toggle('open');
      var t = document.getElementById('advanced-toggle-text');
      t.textContent = s.classList.contains('open') ? '▲ Hide API keys' : '▼ Use your own Alpaca keys';
    }}
    function updateBtn() {{
      var action = document.querySelector('input[name="action"]:checked').value;
      var shares = document.getElementById('shares').value;
      var color = action === 'buy' ? '#10B981' : '#EF4444';
      document.getElementById('submit-btn').style.background = color;
      document.getElementById('submit-btn').textContent = action.toUpperCase() + ' ' + shares + ' share' + (shares == 1 ? '' : 's') + ' of ${ticker}';
    }}
    function changeShares(delta) {{
      var el = document.getElementById('shares');
      el.value = Math.max(1, parseInt(el.value || 1) + delta);
      updateBtn();
    }}
    window.onload = updateBtn;
  </script>
</head>
<body>
  <div class="topbar">
    <div class="topbar-dot"></div>
    <span class="topbar-logo">SentinelIQ</span>
    <span class="topbar-sub">Market Intelligence</span>
  </div>
  <div class="card">
    <h2>Review Your Order</h2>
    <p class="sub">${ticker} &mdash; Alpaca Paper Trade</p>

    <form method="POST" action="/api/v1/trade/confirm?token={token}">
      <label>Order Type</label>
      <div class="toggle">
        <input type="radio" name="action" id="buy" value="buy" {'checked' if action == 'buy' else ''} onchange="updateBtn()">
        <input type="radio" name="action" id="sell" value="sell" {'checked' if action == 'sell' else ''} onchange="updateBtn()">
        <div class="toggle-labels" style="display:flex;flex:1;">
          <label for="buy" class="buy-label" style="flex:1;{'background:#10B981;color:white;' if action=='buy' else ''}">Buy</label>
          <label for="sell" class="sell-label" style="flex:1;{'background:#EF4444;color:white;' if action=='sell' else ''}">Sell</label>
        </div>
      </div>

      <label>Number of Shares</label>
      <div class="shares-row">
        <button type="button" class="shares-btn" onclick="changeShares(-1)">−</button>
        <input type="number" id="shares" name="shares" value="{shares}" min="1" max="9999"
               class="shares-input" oninput="updateBtn()">
        <button type="button" class="shares-btn" onclick="changeShares(1)">+</button>
      </div>

      <button type="button" class="advanced-toggle" onclick="toggleAdvanced()">
        <span id="advanced-toggle-text">▼ Use your own Alpaca keys</span>
      </button>
      <div id="advanced-section" class="advanced-section">
        <label>Alpaca API Key ID</label>
        <input type="password" name="alpaca_key" placeholder="PK..." class="api-input" autocomplete="off">
        <label>Alpaca Secret Key</label>
        <input type="password" name="alpaca_secret" placeholder="••••••••" class="api-input" autocomplete="off">
        <p class="api-hint">Optional — leave blank to use the system account. Your keys are never stored.</p>
      </div>

      <button type="submit" id="submit-btn" class="submit-btn"></button>
    </form>

    <p class="disclaimer">Paper trade only &middot; No real money &middot; Link expires in 1 hour</p>
    <p class="brand">Powered by <span>SentinelIQ</span> &middot; Amazon Nova</p>
  </div>
</body>
</html>"""


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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Inter, system-ui, sans-serif; background: #f8fafc; color: #0f172a;
           display: flex; flex-direction: column; align-items: center; justify-content: center;
           min-height: 100vh; margin: 0; }}
    .topbar {{ position: fixed; top: 0; left: 0; right: 0; height: 56px;
               background: white; border-bottom: 1px solid #e2e8f0;
               display: flex; align-items: center; padding: 0 24px; gap: 8px; }}
    .topbar-logo {{ font-size: 15px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px; }}
    .topbar-sub {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 500; }}
    .topbar-dot {{ width: 6px; height: 6px; border-radius: 50%; background: #10B981; margin-right: 2px; }}
    .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px;
             padding: 48px 40px; max-width: 440px; width: 100%; text-align: center;
             box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04); }}
    .icon {{ width: 56px; height: 56px; border-radius: 50%; background: {color}15;
             display: flex; align-items: center; justify-content: center;
             font-size: 24px; color: {color}; margin: 0 auto 20px; line-height: 56px; }}
    h1 {{ font-size: 18px; font-weight: 700; margin: 0 0 10px; color: #0f172a; }}
    p {{ color: #64748b; font-size: 14px; line-height: 1.6; margin: 0 0 16px; }}
    .badge {{ display: inline-block; background: {action_color}12; color: {action_color};
              border: 1px solid {action_color}30; padding: 3px 12px; border-radius: 6px;
              font-size: 12px; font-weight: 600; letter-spacing: 0.3px; margin-bottom: 18px; }}
    .divider {{ border: none; border-top: 1px solid #f1f5f9; margin: 20px 0; }}
    .brand {{ color: #94a3b8; font-size: 12px; }}
    .brand a {{ color: #10B981; font-weight: 600; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="topbar-dot"></div>
    <span class="topbar-logo">SentinelIQ</span>
    <span class="topbar-sub">Market Intelligence</span>
  </div>
  <div class="card">
    <div class="icon">{icon}</div>
    {badge}
    <h1>{title}</h1>
    <p>{message}</p>
    <hr class="divider"/>
    <p class="brand">Powered by <a href="#">SentinelIQ</a> &middot; Amazon Nova</p>
  </div>
</body>
</html>"""
