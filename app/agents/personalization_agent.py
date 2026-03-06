import json

from app.agents.base_agent import BaseAgent
from app.utils.logger import logger


class PersonalizationAgent(BaseAgent):
    """Agent 4: Matches alert to users who have the ticker in their watchlist."""

    CACHE_TTL = 60  # seconds

    async def run(self, context: dict) -> dict:
        ticker = context.get("ticker", "UNKNOWN")
        nova = context.get("nova_analysis", {})
        confidence = nova.get("confidence_level", 0.5)

        target_users = await self._get_matching_users(ticker, confidence)
        context["target_users"] = target_users

        if not target_users:
            logger.info("no_target_users", ticker=ticker)
            context["passed"] = False

        logger.info("personalization_done", ticker=ticker, user_count=len(target_users))
        return context

    async def _get_matching_users(self, ticker: str, confidence: float) -> list[str]:
        # Try Redis cache first
        try:
            from app.services.cache import cache_get, cache_set, redis_client
            from sqlalchemy import select
            from app.db.session import AsyncSessionLocal
            from app.db.models import WatchlistItem, UserPreferences

            cache_key = f"watchlist_users:{ticker}"
            cached = await cache_get(cache_key)
            if cached:
                user_data = cached
            else:
                async with AsyncSessionLocal() as db:
                    # Users who have this ticker in watchlist
                    result = await db.execute(
                        select(WatchlistItem.user_id).where(WatchlistItem.ticker == ticker)
                    )
                    user_ids = [str(row[0]) for row in result.fetchall()]

                    # Also get preferences to filter by sensitivity
                    prefs_result = await db.execute(
                        select(UserPreferences).where(
                            UserPreferences.user_id.in_([
                                __import__('uuid').UUID(uid) for uid in user_ids
                            ])
                        )
                    )
                    prefs_map = {str(p.user_id): p.alert_sensitivity for p in prefs_result.scalars()}

                    user_data = {"users": user_ids, "prefs": prefs_map}
                    await cache_set(cache_key, user_data, ttl=self.CACHE_TTL)

            # Filter by alert sensitivity
            matching = []
            for uid in user_data.get("users", []):
                sensitivity = user_data.get("prefs", {}).get(uid, 0.5)
                if confidence >= sensitivity:
                    matching.append(uid)

            return matching

        except Exception as e:
            logger.error("personalization_error", error=str(e))
            # Fallback: return demo user if DB unavailable
            return []
