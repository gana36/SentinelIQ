"""
Nova Act SEC EDGAR capture service.

Navigates to SEC EDGAR for a given ticker, screenshots the latest 8-K filings,
and returns raw PNG bytes. Returns None gracefully on any failure.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import os

import structlog

from app.config import settings

logger = structlog.get_logger()


async def capture_sec_filings(ticker: str) -> bytes | None:
    """
    Use Nova Act (headless browser) to screenshot the SEC EDGAR 8-K filing list
    for `ticker`. Returns PNG bytes, or None if Nova Act key is missing / any error.
    """
    if settings.mock_mode or not settings.nova_act_api_key:
        logger.debug("sec_capture_skipped", ticker=ticker,
                     reason="mock_mode or no nova_act_api_key")
        return None

    try:
        from nova_act import NovaAct  # type: ignore[import]
    except ImportError:
        logger.warning("sec_capture_skipped", reason="nova_act_not_installed")
        return None

    url = (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcompany&CIK={ticker}&type=8-K"
        f"&dateb=&owner=include&count=5&search_text="
    )

    os.environ.setdefault("NOVA_ACT_API_KEY", settings.nova_act_api_key)

    def _run_sync() -> bytes:
        with NovaAct(starting_page=url, headless=True) as nova:
            nova.act(
                "Wait for the SEC EDGAR filing results table to fully load. "
                "Do not click anything."
            )
            # Try to screenshot just the results table; fall back to full page
            table = nova.page.locator("table.tableFile2").first
            if table.count() > 0:
                png: bytes = table.screenshot(timeout=20_000)
            else:
                png = nova.page.screenshot(full_page=False)
            return png

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            png_bytes = await loop.run_in_executor(pool, _run_sync)
            logger.info("sec_capture_success", ticker=ticker,
                        size_kb=round(len(png_bytes) / 1024, 1))
            return png_bytes
        except Exception as exc:
            logger.warning("sec_capture_failed", ticker=ticker, error=str(exc))
            return None
