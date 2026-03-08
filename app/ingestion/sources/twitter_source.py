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

POLL_INTERVAL = 1800  # 30 minutes — cost-conscious for Pay Per Use ($0.005/tweet × 10 = $0.05/poll)
TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

# Tickers to track via cashtag — pulled from a static default + any injected tickers
DEFAULT_TICKERS = ["TSLA", "AAPL", "NVDA", "META", "SPY", "MSFT", "AMZN", "GOOGL"]

# Max tweets per poll (API max is 100 per request on Basic tier, 10 on Free)
MAX_RESULTS = 10


def _build_query(tickers: list[str]) -> str:
    """Build Twitter search query for cashtag mentions."""
    cashtags = " OR ".join(f"${t}" for t in tickers[:10])  # API limit on OR clauses
    return f"({cashtags}) lang:en -is:retweet -is:reply"


async def stream() -> AsyncIterator[RawSignal]:
    if not settings.twitter_bearer_token:
        logger.warning("twitter_source_skipped", reason="no TWITTER_BEARER_TOKEN")
        return

    headers = {"Authorization": f"Bearer {settings.twitter_bearer_token}"}
    seen_ids: set[str] = set()

    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            try:
                query = _build_query(DEFAULT_TICKERS)
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
