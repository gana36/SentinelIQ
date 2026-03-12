import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

_quote_cache: dict[str, tuple[float, object]] = {}  # ticker -> (timestamp, QuoteData)
QUOTE_CACHE_TTL = 60  # seconds

from app.config import settings
from app.db.models import User
from app.dependencies import get_current_user
from app.schemas.market import NewsItem, QuoteData
from app.utils.ticker_resolver import resolve_ticker

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote/{ticker}", response_model=QuoteData)
async def get_quote(ticker: str, current_user: User = Depends(get_current_user)):
    ticker = ticker.upper()

    if settings.mock_mode:
        return _mock_quote(ticker)

    # Return cached quote if fresh
    import time
    from app.utils.logger import logger
    cached = _quote_cache.get(ticker)
    if cached and (time.time() - cached[0]) < QUOTE_CACHE_TTL:
        return cached[1]

    # Try yfinance (free, no API key required)
    try:
        import yfinance as yf
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, lambda: yf.Ticker(ticker).fast_info)
        price = info.last_price
        prev_close = info.previous_close
        if price and prev_close:
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            result = QuoteData(
                ticker=ticker,
                price=round(price, 2),
                change_pct=round(change_pct, 2),
                volume=int(info.last_volume or 0),
                volume_zscore=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            _quote_cache[ticker] = (time.time(), result)
            return result
        logger.warning("yfinance_no_price", ticker=ticker, price=price, prev_close=prev_close)
    except Exception as e:
        logger.warning("yfinance_error", ticker=ticker, error=str(e))
        # On rate limit, return stale cache rather than mock
        if cached:
            return cached[1]

    return _mock_quote(ticker)


@router.get("/news", response_model=list[NewsItem])
async def get_news(
    ticker: str | None = Query(None),
    current_user: User = Depends(get_current_user),
):
    if settings.mock_mode:
        return _mock_news(ticker)

    if settings.finlight_api_key:
        try:
            import httpx
            query = ticker if ticker else "stock market earnings"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.finlight.me/v2/articles",
                    headers={"X-API-KEY": settings.finlight_api_key},
                    json={"query": query, "language": "en", "pageSize": 10},
                )
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles", [])
                if articles:
                    from app.utils.logger import logger
                    logger.info("finlight_article_keys", keys=list(articles[0].keys()))
                items = []
                for article in articles:
                    source = article.get("source", "")
                    url = (article.get("url") or article.get("link") or
                           article.get("articleUrl") or article.get("originalUrl") or "")
                    items.append(NewsItem(
                        title=article.get("title", ""),
                        source=source if isinstance(source, str) else source.get("name", ""),
                        url=url,
                        published_at=article.get("publishedAt", article.get("date", "")),
                    ))
                return items if items else _mock_news(ticker)
        except Exception as e:
            from app.utils.logger import logger
            logger.error("finlight_news_error", ticker=ticker, error=str(e))

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
