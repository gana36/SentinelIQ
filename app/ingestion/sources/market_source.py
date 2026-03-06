import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import AsyncIterator

import numpy as np

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger

POLL_INTERVAL = 30
VOLUME_WINDOW = 20
WATCHLIST_REFRESH_INTERVAL = 120  # re-fetch watchlisted tickers every 2 minutes
FALLBACK_TICKERS = ["TSLA", "AAPL", "NVDA", "META", "GOOGL", "SPY"]


async def _get_watched_tickers() -> list[str]:
    """Return the union of all users' watchlists from DB. Falls back to hardcoded list."""
    try:
        from sqlalchemy import select
        from app.db.session import AsyncSessionLocal
        from app.db.models import WatchlistItem

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(WatchlistItem.ticker).distinct())
            tickers = [row[0] for row in result.fetchall()]
            return tickers if tickers else FALLBACK_TICKERS
    except Exception as e:
        logger.warning("watchlist_fetch_failed", error=str(e), fallback=FALLBACK_TICKERS)
        return FALLBACK_TICKERS


async def stream() -> AsyncIterator[RawSignal]:
    if not settings.polygon_api_key:
        logger.warning("market_source_skipped", reason="no POLYGON_API_KEY")
        return

    volume_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=VOLUME_WINDOW))
    watched_tickers = await _get_watched_tickers()
    last_watchlist_refresh = asyncio.get_event_loop().time()
    logger.info("market_source_started", tickers=watched_tickers)

    while True:
        # Refresh watchlist periodically so new watchlist additions are picked up
        now = asyncio.get_event_loop().time()
        if now - last_watchlist_refresh > WATCHLIST_REFRESH_INTERVAL:
            watched_tickers = await _get_watched_tickers()
            last_watchlist_refresh = now
            logger.info("market_watchlist_refreshed", tickers=watched_tickers)

        try:
            from polygon import RESTClient
            client = RESTClient(settings.polygon_api_key)
            loop = asyncio.get_event_loop()

            for ticker in watched_tickers:
                aggs = await loop.run_in_executor(
                    None,
                    lambda t=ticker: list(client.get_aggs(t, 1, "minute", limit=1)),
                )
                if not aggs:
                    continue

                bar = aggs[0]
                volume = bar.volume or 0
                price = bar.close or 0
                prev_price = bar.open or price

                vol_hist = volume_history[ticker]
                vol_hist.append(volume)

                zscore = 0.0
                if len(vol_hist) >= 5:
                    arr = np.array(vol_hist)
                    mean, std = arr.mean(), arr.std()
                    zscore = float((volume - mean) / std) if std > 0 else 0.0

                change_pct = ((price - prev_price) / prev_price * 100) if prev_price else 0

                if abs(zscore) > 2.0:  # only emit on notable volume
                    text = (
                        f"${ticker} showing unusual volume. Current: {volume:,} "
                        f"(z-score: {zscore:.2f}), price change: {change_pct:+.2f}%"
                    )
                    yield RawSignal(
                        source="market",
                        ticker=ticker,
                        raw_text=text,
                        timestamp=datetime.now(timezone.utc),
                        metadata={
                            "price": price,
                            "volume": volume,
                            "volume_zscore": zscore,
                            "change_pct": change_pct,
                        },
                    )
        except Exception as e:
            logger.error("market_source_error", error=str(e))

        await asyncio.sleep(POLL_INTERVAL)
