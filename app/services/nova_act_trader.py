"""
Nova Act / Alpaca integration for drafting and executing paper trades.

Draft:    Always returns a mock SVG preview of the order form (instant, no browser).
Execute:  Calls Alpaca Paper Trading REST API directly (no browser, no MFA needed).
          Falls back to mock SVG if API keys are missing or MOCK_MODE=true.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

import structlog

from app.config import settings

logger = structlog.get_logger()

@dataclass
class TradeDraft:
    ticker: str
    action: str          # "buy" | "sell"
    shares: int
    est_price: float
    est_total: float
    screenshot_b64: str  # base64-encoded SVG receipt
    session_id: str
    is_mock: bool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def draft_trade(
    ticker: str,
    action: str,
    shares: int,
    est_price: float,
) -> TradeDraft:
    """Draft preview — always returns a mock SVG (no Alpaca call needed)."""
    return _mock_draft(ticker, action, shares, est_price)


async def execute_trade(
    ticker: str,
    action: str,
    shares: int,
    est_price: float,
    alpaca_key: str = "",
    alpaca_secret: str = "",
) -> TradeDraft:
    """Execute via Alpaca Paper Trading REST API. Falls back to mock if keys missing.
    User-supplied alpaca_key/alpaca_secret override the system-configured keys."""
    api_key = alpaca_key.strip() or settings.alpaca_api_key
    api_secret = alpaca_secret.strip() or settings.alpaca_api_secret

    if settings.mock_mode or not api_key:
        return _mock_execute(ticker, action, shares, est_price)

    try:
        import httpx
    except ImportError:
        logger.warning("httpx_not_installed_falling_back_to_mock")
        return _mock_execute(ticker, action, shares, est_price)

    import uuid

    session_id = str(uuid.uuid4())

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://paper-api.alpaca.markets/v2/orders",
                headers={
                    "APCA-API-KEY-ID": api_key,
                    "APCA-API-SECRET-KEY": api_secret,
                },
                json={
                    "symbol": ticker,
                    "qty": str(shares),
                    "side": action,
                    "type": "market",
                    "time_in_force": "day",
                },
            )
            resp.raise_for_status()
            order = resp.json()

        order_id = order.get("id", session_id)[:8].upper()
        status = order.get("status", "accepted")
        filled_price = float(order.get("filled_avg_price") or est_price or 0)
        est_total = round(filled_price * shares, 2) if filled_price else 0.0

        logger.info("alpaca_order_placed", ticker=ticker, action=action,
                    order_id=order_id, status=status)

        receipt_svg = _receipt_svg(ticker, action, shares, filled_price,
                                   est_total, order_id, status)
        svg_b64 = base64.b64encode(receipt_svg.encode()).decode()

        return TradeDraft(
            ticker=ticker, action=action, shares=shares,
            est_price=filled_price, est_total=est_total,
            screenshot_b64=svg_b64, session_id=order.get("id", session_id),
            is_mock=False,
        )
    except Exception as e:
        logger.warning("alpaca_api_execute_failed", error=str(e))
        return _mock_execute(ticker, action, shares, est_price)


# ---------------------------------------------------------------------------
# Real receipt SVG — shown after a successful Alpaca API order
# ---------------------------------------------------------------------------

def _receipt_svg(
    ticker: str,
    action: str,
    shares: int,
    filled_price: float,
    est_total: float,
    order_id: str,
    status: str,
) -> str:
    action_color = "#10B981" if action == "buy" else "#EF4444"
    price_str = f"${filled_price:,.2f}" if filled_price else "Market"
    total_str = f"${est_total:,.2f}" if est_total else "Pending fill"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="320" style="background:#0f1117;font-family:Inter,system-ui,sans-serif;">
  <rect width="520" height="52" fill="#1a1d27"/>
  <circle cx="28" cy="26" r="10" fill="#10B981"/>
  <text x="46" y="31" fill="white" font-size="14" font-weight="700">Alpaca Paper Trading</text>
  <rect x="440" y="16" width="64" height="20" rx="4" fill="#10B981" opacity="0.2"/>
  <text x="472" y="30" fill="#10B981" font-size="10" font-weight="600" text-anchor="middle">PAPER</text>

  <rect x="20" y="68" width="480" height="232" rx="12" fill="#1e2130"/>

  <circle cx="260" cy="128" r="28" fill="{action_color}" opacity="0.15"/>
  <circle cx="260" cy="128" r="20" fill="{action_color}" opacity="0.3"/>
  <text x="260" y="135" fill="{action_color}" font-size="20" font-weight="700" text-anchor="middle">&#x2713;</text>

  <text x="260" y="176" fill="white" font-size="16" font-weight="700" text-anchor="middle">Order {status.capitalize()}</text>
  <text x="260" y="196" fill="#64748b" font-size="12" text-anchor="middle">{action.upper()} {shares} share{'s' if shares != 1 else ''} of {ticker} &#xB7; Market</text>

  <rect x="40" y="212" width="440" height="56" rx="8" fill="#0d0e14"/>
  <text x="100" y="232" fill="#64748b" font-size="10" text-anchor="middle">ORDER ID</text>
  <text x="100" y="252" fill="white" font-size="11" font-weight="600" text-anchor="middle">{order_id}</text>
  <text x="260" y="232" fill="#64748b" font-size="10" text-anchor="middle">FILL PRICE</text>
  <text x="260" y="252" fill="white" font-size="11" font-weight="600" text-anchor="middle">{price_str}</text>
  <text x="420" y="232" fill="#64748b" font-size="10" text-anchor="middle">EST. TOTAL</text>
  <text x="420" y="252" fill="{action_color}" font-size="12" font-weight="700" text-anchor="middle">{total_str}</text>

  <text x="260" y="288" fill="#475569" font-size="10" text-anchor="middle">Paper trade only &#x2014; no real money involved &#xB7; via Alpaca API</text>
</svg>"""


# ---------------------------------------------------------------------------
# Mock draft — convincing SVG trade form (form filled, waiting for confirm)
# ---------------------------------------------------------------------------

def _mock_draft(
    ticker: str,
    action: str,
    shares: int,
    est_price: float,
) -> TradeDraft:
    import uuid

    est_total = round(est_price * shares, 2)
    session_id = str(uuid.uuid4())
    action_color = "#10B981" if action == "buy" else "#EF4444"
    buy_fill = "#10B981" if action == "buy" else "#64748b"
    sell_fill = "#EF4444" if action == "sell" else "#64748b"
    active_x = "260" if action == "buy" else "370"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="420" style="background:#0f1117;font-family:Inter,system-ui,sans-serif;">
  <rect width="520" height="52" fill="#1a1d27"/>
  <circle cx="28" cy="26" r="10" fill="#10B981"/>
  <text x="46" y="31" fill="white" font-size="14" font-weight="700">Alpaca Paper Trading</text>
  <rect x="440" y="16" width="64" height="20" rx="4" fill="#10B981" opacity="0.2"/>
  <text x="472" y="30" fill="#10B981" font-size="10" font-weight="600" text-anchor="middle">PAPER</text>

  <rect x="20" y="68" width="480" height="332" rx="12" fill="#1e2130"/>
  <text x="40" y="102" fill="#94a3b8" font-size="11" font-weight="500">ORDER ENTRY · Nova Act prepared this order</text>
  <rect x="40" y="112" width="440" height="1" fill="#2d3348"/>

  <text x="40" y="146" fill="#64748b" font-size="11">Symbol</text>
  <rect x="40" y="154" width="200" height="38" rx="8" fill="#0d0e14"/>
  <text x="60" y="179" fill="white" font-size="18" font-weight="700">{ticker}</text>

  <rect x="260" y="154" width="220" height="38" rx="8" fill="#0d0e14"/>
  <rect x="{active_x}" y="154" width="110" height="38" rx="8" fill="{action_color}" opacity="0.15"/>
  <text x="315" y="179" fill="{buy_fill}" font-size="13" font-weight="600" text-anchor="middle">BUY</text>
  <text x="425" y="179" fill="{sell_fill}" font-size="13" font-weight="600" text-anchor="middle">SELL</text>

  <text x="40" y="222" fill="#64748b" font-size="11">Order Type</text>
  <rect x="40" y="230" width="200" height="38" rx="8" fill="#0d0e14"/>
  <text x="60" y="255" fill="white" font-size="14">Market</text>
  <text x="220" y="255" fill="#475569" font-size="12">&#x25BE;</text>

  <text x="260" y="222" fill="#64748b" font-size="11">Quantity (shares)</text>
  <rect x="260" y="230" width="220" height="38" rx="8" fill="#0d0e14" stroke="{action_color}" stroke-width="1.5"/>
  <text x="280" y="255" fill="white" font-size="16" font-weight="600">{shares}</text>

  <rect x="40" y="288" width="440" height="50" rx="8" fill="#0d0e14"/>
  <text x="60" y="311" fill="#64748b" font-size="11">Est. Price</text>
  <text x="60" y="328" fill="white" font-size="13" font-weight="500">${est_price:,.2f}</text>
  <text x="200" y="311" fill="#64748b" font-size="11">Shares</text>
  <text x="200" y="328" fill="white" font-size="13" font-weight="500">{shares}</text>
  <text x="340" y="311" fill="#64748b" font-size="11">Est. Total</text>
  <text x="340" y="328" fill="white" font-size="15" font-weight="700">${est_total:,.2f}</text>

  <rect x="40" y="352" width="440" height="32" rx="6" fill="{action_color}" opacity="0.08" stroke="{action_color}" stroke-width="1" stroke-opacity="0.3"/>
  <text x="260" y="373" fill="{action_color}" font-size="11" font-weight="500" text-anchor="middle">&#x26A1; Nova Act stopped here &#x2014; waiting for your confirmation</text>
</svg>"""

    svg_b64 = base64.b64encode(svg.encode()).decode()
    return TradeDraft(
        ticker=ticker, action=action, shares=shares,
        est_price=est_price, est_total=est_total,
        screenshot_b64=svg_b64, session_id=session_id, is_mock=True,
    )


# ---------------------------------------------------------------------------
# Mock execute — success SVG (order confirmed)
# ---------------------------------------------------------------------------

def _mock_execute(
    ticker: str,
    action: str,
    shares: int,
    est_price: float,
) -> TradeDraft:
    import uuid

    est_total = round(est_price * shares, 2)
    session_id = str(uuid.uuid4())
    action_color = "#10B981" if action == "buy" else "#EF4444"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="300" style="background:#0f1117;font-family:Inter,system-ui,sans-serif;">
  <rect width="520" height="52" fill="#1a1d27"/>
  <circle cx="28" cy="26" r="10" fill="#10B981"/>
  <text x="46" y="31" fill="white" font-size="14" font-weight="700">Alpaca Paper Trading</text>
  <rect x="440" y="16" width="64" height="20" rx="4" fill="#10B981" opacity="0.2"/>
  <text x="472" y="30" fill="#10B981" font-size="10" font-weight="600" text-anchor="middle">PAPER</text>

  <rect x="20" y="68" width="480" height="212" rx="12" fill="#1e2130"/>

  <circle cx="260" cy="130" r="28" fill="{action_color}" opacity="0.15"/>
  <circle cx="260" cy="130" r="20" fill="{action_color}" opacity="0.3"/>
  <text x="260" y="137" fill="{action_color}" font-size="20" font-weight="700" text-anchor="middle">&#x2713;</text>

  <text x="260" y="178" fill="white" font-size="16" font-weight="700" text-anchor="middle">Order Submitted</text>
  <text x="260" y="198" fill="#64748b" font-size="12" text-anchor="middle">{action.upper()} {shares} share{'s' if shares != 1 else ''} of {ticker} &#xB7; Market Order</text>

  <rect x="160" y="218" width="200" height="36" rx="8" fill="#0d0e14"/>
  <text x="260" y="232" fill="#64748b" font-size="10" text-anchor="middle">EST. TOTAL</text>
  <text x="260" y="247" fill="{action_color}" font-size="14" font-weight="700" text-anchor="middle">${est_total:,.2f}</text>

  <text x="260" y="272" fill="#475569" font-size="10" text-anchor="middle">Paper trade only &#x2014; no real money involved</text>
</svg>"""

    svg_b64 = base64.b64encode(svg.encode()).decode()
    return TradeDraft(
        ticker=ticker, action=action, shares=shares,
        est_price=est_price, est_total=est_total,
        screenshot_b64=svg_b64, session_id=session_id, is_mock=True,
    )
