import uuid
from datetime import datetime, timezone

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.schemas.alert import ActionCard
from app.utils.logger import logger


class ActionComposerAgent(BaseAgent):
    """Agent 5: Assembles the final ActionCard with FAISS similar events."""

    async def run(self, context: dict) -> dict:
        signal = context["signal"]
        ticker = context.get("ticker", "UNKNOWN")

        # Retrieve similar historical events
        similar_events = await self._get_similar_events(signal.raw_text)

        # Build source links list
        source_links = []
        if signal.metadata.get("url"):
            source_links.append(signal.metadata["url"])

        action_card = ActionCard(
            alert_id=str(uuid.uuid4()),
            ticker=ticker,
            event_summary=context.get("nova_analysis", {}).get(
                "event_summary", f"Anomalous signal detected for {ticker}"
            ),
            sentiment=context.get("sentiment", {}),
            anomaly=context.get("anomaly", {}),
            nova_analysis=context.get("nova_analysis", {}),
            similar_events=similar_events,
            credibility_score=context.get("credibility_score", 0.5),
            source_links=source_links,
            target_users=context.get("target_users", []),
            timestamp=datetime.now(timezone.utc).isoformat(),
            voice_ready=True,
        )

        context["action_card"] = action_card
        logger.info("action_card_composed", ticker=ticker, alert_id=action_card.alert_id)
        return context

    async def _get_similar_events(self, text: str) -> list[dict]:
        if settings.mock_mode:
            from app.ml.embeddings.mock_embeddings import mock_search
            return mock_search(text)

        try:
            from app.ml.embeddings.nova_embeddings import embed_text
            from app.ml.embeddings.faiss_store import search
            vec = await embed_text(text)
            return search(vec, k=3)
        except Exception as e:
            logger.error("faiss_search_error", error=str(e))
            from app.ml.embeddings.mock_embeddings import mock_search
            return mock_search(text)
