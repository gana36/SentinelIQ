from datetime import datetime, timezone
from typing import AsyncIterator

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger
from app.utils.ticker_resolver import resolve_ticker

SUBREDDITS = "stocks+wallstreetbets+investing"


async def stream() -> AsyncIterator[RawSignal]:
    if not settings.reddit_client_id:
        logger.warning("reddit_source_skipped", reason="no credentials")
        return

    try:
        import asyncpraw
    except ImportError:
        logger.error("asyncpraw_not_installed")
        return

    reddit = asyncpraw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )
    try:
        subreddit = await reddit.subreddit(SUBREDDITS)
        async for submission in subreddit.stream.submissions(skip_existing=True):
            text = f"{submission.title} {submission.selftext or ''}"
            ticker = resolve_ticker(text)
            signal = RawSignal(
                source="reddit",
                ticker=ticker,
                raw_text=text[:1000],
                timestamp=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                metadata={
                    "subreddit": submission.subreddit.display_name,
                    "url": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                    "author": str(submission.author),
                },
            )
            yield signal
    finally:
        await reddit.close()
