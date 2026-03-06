from app.agents.base_agent import BaseAgent
from app.utils.logger import logger

# Source domain credibility weights (0.0–1.0)
_SOURCE_SCORES = {
    "reuters.com": 0.95,
    "bloomberg.com": 0.93,
    "wsj.com": 0.92,
    "ft.com": 0.90,
    "cnbc.com": 0.85,
    "sec": 0.98,        # SEC EDGAR filings
    "news": 0.70,       # generic NewsAPI
    "market": 0.80,     # Polygon.io market data
    "reddit": 0.45,
    "twitter": 0.40,
    "mock": 0.75,
    "unknown": 0.30,
}


class CredibilityCheckerAgent(BaseAgent):
    """Agent 2: Scores source reliability and checks multi-source confirmation."""

    PASS_THRESHOLD = 0.3

    async def run(self, context: dict) -> dict:
        signal = context["signal"]
        source = signal.source

        # Base score from source type
        base_score = _SOURCE_SCORES.get(source, _SOURCE_SCORES["unknown"])

        # Domain check for news articles
        url = signal.metadata.get("url", "")
        for domain, score in _SOURCE_SCORES.items():
            if domain in url:
                base_score = score
                break

        # Multi-source confirmation via Redis counter
        multi_source_bonus = 0.0
        try:
            from app.services.cache import redis_client
            ticker = context.get("ticker", "UNKNOWN")
            counter_key = f"credibility:{ticker}:{_time_window()}"
            count = await redis_client.incr(counter_key)
            await redis_client.expire(counter_key, 300)  # 5-minute window
            if count > 1:
                multi_source_bonus = min(0.2 * (count - 1), 0.3)
        except Exception:
            pass

        credibility_score = min(base_score + multi_source_bonus, 1.0)
        context["credibility_score"] = credibility_score
        context["source_count"] = 1

        if credibility_score < self.PASS_THRESHOLD:
            logger.info("credibility_failed", source=source, score=credibility_score)
            context["passed"] = False

        logger.info("credibility_checked", source=source, score=credibility_score)
        return context


def _time_window() -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return f"{now.hour}:{now.minute // 5}"  # 5-minute buckets
