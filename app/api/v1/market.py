import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.db.models import User
from app.dependencies import get_current_user
from app.schemas.market import NewsItem, QuoteData
from app.utils.ticker_resolver import resolve_ticker

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote/{ticker}", response_model=QuoteData)
async def get_quote(ticker: str, current_user: User = Depends(get_current_user)):
    ticker = ticker.upper()

    if settings.mock_mode or not settings.polygon_api_key:
        return _mock_quote(ticker)

    try:
        from polygon import RESTClient
        client = RESTClient(settings.polygon_api_key)
        loop = asyncio.get_event_loop()
        aggs = await loop.run_in_executor(None, lambda: list(client.get_aggs(ticker, 1, "minute", limit=1)))
        if aggs:
            bar = aggs[0]
            change_pct = ((bar.close - bar.open) / bar.open * 100) if bar.open else 0
            return QuoteData(
                ticker=ticker,
                price=bar.close,
                change_pct=round(change_pct, 2),
                volume=bar.volume,
                volume_zscore=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception:
        pass

    return _mock_quote(ticker)


@router.get("/news", response_model=list[NewsItem])
async def get_news(
    ticker: str | None = Query(None),
    current_user: User = Depends(get_current_user),
):
    if settings.mock_mode or not settings.newsapi_key:
        return _mock_news(ticker)

    try:
        from newsapi import NewsApiClient
        client = NewsApiClient(api_key=settings.newsapi_key)
        query = ticker if ticker else "stock market"
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.get_everything(q=query, language="en", sort_by="publishedAt", page_size=10),
        )
        items = []
        for article in response.get("articles", []):
            items.append(NewsItem(
                title=article.get("title", ""),
                source=article.get("source", {}).get("name", ""),
                url=article.get("url", ""),
                published_at=article.get("publishedAt", ""),
            ))
        return items
    except Exception:
        return _mock_news(ticker)


def _mock_quote(ticker: str) -> QuoteData:
    import hashlib
    h = int(hashlib.md5(ticker.encode()).hexdigest(), 16)
    base_price = 50 + (h % 950)
    change = (h % 20 - 10) / 10  # -1.0% to +1.0%
    return QuoteData(
        ticker=ticker,
        price=round(base_price + change, 2),
        change_pct=round(change, 2),
        volume=100000 + (h % 5000000),
        volume_zscore=round((h % 30 - 15) / 10, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _mock_news(ticker: str | None) -> list[NewsItem]:
    t = ticker or "MARKET"
    return [
        NewsItem(
            title=f"Analysts weigh in on {t} after recent volatility",
            source="Mock Financial News",
            url="https://example.com/news/1",
            published_at=datetime.now(timezone.utc).isoformat(),
        ),
        NewsItem(
            title=f"Institutional investors increase positions in {t}",
            source="Mock Market Watch",
            url="https://example.com/news/2",
            published_at=datetime.now(timezone.utc).isoformat(),
        ),
    ]
