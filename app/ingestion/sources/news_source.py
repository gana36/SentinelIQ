import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger
from app.utils.ticker_resolver import resolve_ticker

POLL_INTERVAL = settings.demo_news_poll_interval_seconds if settings.demo_mode else 300  # demo: 30s, prod: 300s
FINLIGHT_URL = "https://api.finlight.me/v2/articles"
NEWSAPI_QUERY = "stock OR earnings OR SEC OR market OR Federal Reserve"


async def _fetch_finlight(client: httpx.AsyncClient, seen_urls: set) -> list[RawSignal]:
    """Fetch articles from Finlight API."""
    signals = []
    try:
        resp = await client.post(
            FINLIGHT_URL,
            headers={"X-API-KEY": settings.finlight_api_key},
            json={"query": "stock OR earnings OR market", "language": "en", "pageSize": 20},
            timeout=15.0,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        for article in articles:
            url = article.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = article.get("title", "")
            summary = article.get("description", "") or article.get("summary", "")
            text = f"{title} {summary}".strip()
            ticker = resolve_ticker(text)
            source_name = article.get("source", "") if isinstance(article.get("source"), str) else article.get("source", {}).get("name", "")
            signals.append(RawSignal(
                source="news",
                ticker=ticker,
                raw_text=text[:800],
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "url": url,
                    "source_name": source_name,
                    "published_at": article.get("publishedAt", article.get("date", "")),
                },
            ))
    except Exception as e:
        logger.error("finlight_source_error", error=str(e))
    return signals


async def _fetch_newsapi(seen_urls: set) -> list[RawSignal]:
    """Fallback: fetch articles from NewsAPI."""
    signals = []
    try:
        from newsapi import NewsApiClient
        client = NewsApiClient(api_key=settings.newsapi_key)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.get_everything(
                q=NEWSAPI_QUERY,
                language="en",
                sort_by="publishedAt",
                page_size=20,
            ),
        )
        for article in response.get("articles", []):
            url = article.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            text = f"{article.get('title', '')} {article.get('description', '')}".strip()
            ticker = resolve_ticker(text)
            signals.append(RawSignal(
                source="news",
                ticker=ticker,
                raw_text=text[:800],
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "url": url,
                    "source_name": article.get("source", {}).get("name", ""),
                    "published_at": article.get("publishedAt", ""),
                },
            ))
    except Exception as e:
        logger.error("newsapi_source_error", error=str(e))
    return signals


async def stream() -> AsyncIterator[RawSignal]:
    use_finlight = bool(settings.finlight_api_key)
    use_newsapi = bool(settings.newsapi_key)

    if not use_finlight and not use_newsapi:
        logger.warning("news_source_skipped", reason="no FINLIGHT_API_KEY or NEWSAPI_KEY")
        return

    if use_finlight:
        logger.info("news_source_using_finlight")
    else:
        logger.info("news_source_using_newsapi_fallback")

    seen_urls: set[str] = set()

    async with httpx.AsyncClient() as client:
        while True:
            if use_finlight:
                signals = await _fetch_finlight(client, seen_urls)
            else:
                signals = await _fetch_newsapi(seen_urls)

            for signal in signals:
                yield signal

            await asyncio.sleep(POLL_INTERVAL)
