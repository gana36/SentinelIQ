import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

import feedparser

from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger
from app.utils.ticker_resolver import resolve_ticker

SEC_FEED_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=10&output=atom"
POLL_INTERVAL = 120  # 2 minutes


async def stream() -> AsyncIterator[RawSignal]:
    seen_ids: set[str] = set()

    while True:
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, SEC_FEED_URL)

            for entry in feed.entries:
                entry_id = entry.get("id", entry.get("link", ""))
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)

                title = entry.get("title", "")
                summary = entry.get("summary", "")
                text = f"SEC 8-K Filing: {title}. {summary}"
                ticker = resolve_ticker(text)

                yield RawSignal(
                    source="sec",
                    ticker=ticker,
                    raw_text=text[:800],
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "url": entry.get("link", ""),
                        "filing_type": "8-K",
                        "company": title,
                    },
                )
        except Exception as e:
            logger.error("sec_source_error", error=str(e))

        await asyncio.sleep(POLL_INTERVAL)
