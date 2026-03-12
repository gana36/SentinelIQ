"""
Twitter/X API v2 source — searches cashtag mentions for watchlist tickers.

Uses the recent search endpoint with Bearer token auth. Polls every 5 minutes.
Catches signals that news APIs miss (breaking reactions, influencer takes, etc.)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger
from app.utils.ticker_resolver import resolve_ticker

POLL_INTERVAL = settings.demo_twitter_poll_interval_seconds if settings.demo_mode else 1800  # demo: 60s, prod: 1800s
TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
WATCHLIST_REFRESH_INTERVAL = 300  # re-fetch watchlisted tickers every 5 minutes

FALLBACK_TICKERS = ["AAPL"]

# Max tweets per poll (API max is 100 per request on Basic tier, 10 on Free)
MAX_RESULTS = 10


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
        logger.warning("twitter_watchlist_fetch_failed", error=str(e))
        return FALLBACK_TICKERS


def _build_query(tickers: list[str]) -> str:
    """Build Twitter search query for cashtag mentions. API limits OR clauses to ~10."""
    cashtags = " OR ".join(f"${t}" for t in tickers[:10])
    return f"({cashtags}) lang:en -is:retweet -is:reply"


async def stream() -> AsyncIterator[RawSignal]:
    if not settings.twitter_bearer_token:
        logger.warning("twitter_source_skipped", reason="no TWITTER_BEARER_TOKEN")
        return

    headers = {"Authorization": f"Bearer {settings.twitter_bearer_token}"}
    seen_ids: set[str] = set()
    watched_tickers = await _get_watched_tickers()
    last_watchlist_refresh = asyncio.get_event_loop().time()

    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            # Refresh watchlist periodically so new user tickers are picked up
            now = asyncio.get_event_loop().time()
            if now - last_watchlist_refresh >= WATCHLIST_REFRESH_INTERVAL:
                watched_tickers = await _get_watched_tickers()
                last_watchlist_refresh = now
                logger.info("twitter_watchlist_refreshed", ticker_count=len(watched_tickers))

            try:
                query = _build_query(watched_tickers)
                params = {
                    "query": query,
                    "max_results": MAX_RESULTS,
                    "tweet.fields": "created_at,author_id,public_metrics,entities",
                    "expansions": "author_id",
                    "user.fields": "username,verified",
                }

                resp = await client.get(
                    TWITTER_SEARCH_URL,
                    headers=headers,
                    params=params,
                )

                if resp.status_code == 402:
                    logger.warning("twitter_source_disabled", reason="credits_depleted_or_plan_required")
                    return  # Stop polling — no point retrying without credits

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("x-rate-limit-reset", 900))
                    logger.warning("twitter_rate_limited", retry_after_s=retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code != 200:
                    logger.error("twitter_api_error", status=resp.status_code, body=resp.text[:200])
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                data = resp.json()
                tweets = data.get("data", [])
                users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
                logger.info("twitter_poll_success", tweet_count=len(tweets))

                for tweet in tweets:
                    tweet_id = tweet["id"]
                    if tweet_id in seen_ids:
                        continue
                    seen_ids.add(tweet_id)

                    text = tweet.get("text", "")
                    author = users.get(tweet.get("author_id", ""), {})
                    username = author.get("username", "unknown")
                    metrics = tweet.get("public_metrics", {})

                    # Detect mentioned ticker from text (cashtags)
                    ticker = None
                    entities = tweet.get("entities", {})
                    cashtag_entities = entities.get("cashtags", [])
                    if cashtag_entities:
                        ticker = cashtag_entities[0].get("tag", "").upper()
                    if not ticker:
                        ticker = resolve_ticker(text)

                    created_at = tweet.get("created_at", "")
                    ts = datetime.now(timezone.utc)
                    if created_at:
                        try:
                            ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    yield RawSignal(
                        source="twitter",
                        ticker=ticker,
                        raw_text=text[:800],
                        timestamp=ts,
                        metadata={
                            "tweet_id": tweet_id,
                            "url": f"https://x.com/{username}/status/{tweet_id}",
                            "username": username,
                            "verified": author.get("verified", False),
                            "likes": metrics.get("like_count", 0),
                            "retweets": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                        },
                    )

                # Trim seen_ids to avoid unbounded growth
                if len(seen_ids) > 5000:
                    seen_ids = set(list(seen_ids)[-2000:])

            except Exception as exc:
                logger.error("twitter_source_error", error=str(exc))

            await asyncio.sleep(POLL_INTERVAL)
