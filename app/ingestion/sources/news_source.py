import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger
from app.utils.ticker_resolver import resolve_ticker

POLL_INTERVAL = 60  # seconds
QUERY = "stock OR earnings OR SEC OR market OR Federal Reserve"


async def stream() -> AsyncIterator[RawSignal]:
    if not settings.newsapi_key:
        logger.warning("news_source_skipped", reason="no NEWSAPI_KEY")
        return

    from newsapi import NewsApiClient
    client = NewsApiClient(api_key=settings.newsapi_key)
    seen_urls: set[str] = set()

    while True:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.get_everything(
                    q=QUERY,
                    language="en",
                    sort_by="publishedAt",
                    page_size=20,
                ),
            )
            articles = response.get("articles", [])
            for article in articles:
                url = article.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                text = f"{article.get('title', '')} {article.get('description', '')}"
                ticker = resolve_ticker(text)

                yield RawSignal(
                    source="news",
                    ticker=ticker,
                    raw_text=text[:800],
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "url": url,
                        "source_name": article.get("source", {}).get("name", ""),
                        "published_at": article.get("publishedAt", ""),
                    },
                )
        except Exception as e:
            logger.error("news_source_error", error=str(e))

        await asyncio.sleep(POLL_INTERVAL)
