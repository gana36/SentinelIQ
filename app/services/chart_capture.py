"""
Nova Act chart capture service.

Navigates to TradingView for a given ticker, screenshots the chart,
and returns raw PNG bytes. Returns None gracefully on any failure.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import os

import structlog

from app.config import settings

logger = structlog.get_logger()


async def capture_tradingview_chart(ticker: str) -> bytes | None:
    """
    Use Nova Act (headless browser) to screenshot the TradingView chart for `ticker`.
    Returns PNG bytes, or None if Nova Act key is missing / any error occurs.
    """
    if settings.mock_mode or not settings.nova_act_api_key:
        logger.debug("chart_capture_skipped", ticker=ticker,
                     reason="mock_mode or no nova_act_api_key")
        return None

    try:
        from nova_act import NovaAct  # type: ignore[import]
    except ImportError:
        logger.warning("chart_capture_skipped", reason="nova_act_not_installed")
        return None

    url = f"https://www.tradingview.com/chart/?symbol={ticker}"

    # Nova Act reads the API key from the NOVA_ACT_API_KEY environment variable
    os.environ.setdefault("NOVA_ACT_API_KEY", settings.nova_act_api_key)

    def _run_sync() -> bytes:
        with NovaAct(
            starting_page=url,
            headless=True,
        ) as nova:
            # Dismiss cookie / GDPR consent banner if present
            nova.act(
                "If there is a cookie consent banner, privacy notice, "
                "or any blocking dialog, click Accept or Close to dismiss it."
            )
            # Wait for the candlestick chart to be rendered
            nova.act(
                "Wait until the candlestick price chart is fully visible and rendered. "
                "Do not interact with any menus or buttons."
            )
            # Screenshot just the chart container
            chart_el = nova.page.locator(".chart-container").first
            png: bytes = chart_el.screenshot(timeout=30_000)
            return png

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            png_bytes = await loop.run_in_executor(pool, _run_sync)
            logger.info("chart_capture_success", ticker=ticker,
                        size_kb=round(len(png_bytes) / 1024, 1))
            return png_bytes
        except Exception as exc:
            logger.warning("chart_capture_failed", ticker=ticker, error=str(exc))
            return None
