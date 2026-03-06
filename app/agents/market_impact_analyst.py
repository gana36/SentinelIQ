from app.agents.base_agent import BaseAgent
from app.services.nova_reasoning import analyze
from app.utils.logger import logger


class MarketImpactAnalystAgent(BaseAgent):
    """Agent 3: Calls Nova Lite to produce structured market impact analysis."""

    async def run(self, context: dict) -> dict:
        nova_analysis = await analyze(context)
        context["nova_analysis"] = nova_analysis
        logger.info(
            "nova_analysis_done",
            ticker=context.get("ticker"),
            confidence=nova_analysis.get("confidence_level"),
            time_horizon=nova_analysis.get("time_horizon"),
        )
        return context
