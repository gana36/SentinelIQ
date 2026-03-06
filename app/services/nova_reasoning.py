import json
import re
from typing import Any

from app.config import settings
from app.utils.logger import logger

SYSTEM_PROMPT = """You are a financial intelligence analyst. Given a market signal, produce a structured JSON analysis.
Respond ONLY with valid JSON — no markdown fences, no extra text."""

USER_TEMPLATE = """Signal details:
- Ticker: {ticker}
- Sentiment: {sentiment_label} (confidence: {sentiment_confidence:.0%})
- Anomaly score: {anomaly_score:.3f} (is_anomaly: {is_anomaly})
- Source: {source}
- Credibility: {credibility_score:.0%}
- Text: "{raw_text}"

Produce this JSON:
{{
  "event_summary": "1-2 sentence summary of what happened",
  "affected_tickers": ["{ticker}"],
  "primary_driver": "key cause of this signal",
  "sector_impact": "which sector and how",
  "confidence_level": 0.0,
  "risk_factors": ["factor1", "factor2"],
  "time_horizon": "intraday",
  "recommended_actions": ["Monitor", "Review position"]
}}"""


async def analyze(context: dict) -> dict[str, Any]:
    """Call Nova Lite and return structured analysis dict."""
    if settings.mock_mode:
        return _mock_analysis(context)

    prompt = USER_TEMPLATE.format(
        ticker=context.get("ticker", "UNKNOWN"),
        sentiment_label=context.get("sentiment", {}).get("label", "neutral"),
        sentiment_confidence=context.get("sentiment", {}).get("confidence", 0.5),
        anomaly_score=context.get("anomaly", {}).get("anomaly_score", 0.0),
        is_anomaly=context.get("anomaly", {}).get("is_anomaly", False),
        source=context.get("signal").source if context.get("signal") else "unknown",
        credibility_score=context.get("credibility_score", 0.5),
        raw_text=(context.get("signal").raw_text[:300] if context.get("signal") else ""),
    )

    try:
        from app.services.bedrock_client import get_bedrock_client
        import asyncio

        client = get_bedrock_client()
        loop = asyncio.get_event_loop()

        def _call():
            return client.converse(
                modelId=settings.bedrock_nova_lite_model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
            )

        response = await loop.run_in_executor(None, _call)
        raw_text = response["output"]["message"]["content"][0]["text"]
        # Strip any accidental markdown
        raw_text = re.sub(r"```(?:json)?", "", raw_text).strip()
        return json.loads(raw_text)
    except Exception as e:
        logger.error("nova_reasoning_error", error=str(e))
        return _mock_analysis(context)


def _mock_analysis(context: dict) -> dict[str, Any]:
    ticker = context.get("ticker", "UNKNOWN")
    sentiment = context.get("sentiment", {})
    label = sentiment.get("label", "neutral")
    confidence = sentiment.get("confidence", 0.5)

    impact_map = {
        "positive": ("increased investor confidence", "potential upward pressure"),
        "negative": ("market concern", "potential downward pressure"),
        "neutral": ("mixed signals", "monitoring recommended"),
    }
    driver, impact = impact_map.get(label, impact_map["neutral"])

    return {
        "event_summary": f"Anomalous {label} signal detected for {ticker} with {confidence:.0%} confidence.",
        "affected_tickers": [ticker],
        "primary_driver": driver,
        "sector_impact": impact,
        "confidence_level": round(confidence * 0.9, 2),
        "risk_factors": ["Market volatility", "Information uncertainty", "Sentiment reversal risk"],
        "time_horizon": "intraday",
        "recommended_actions": ["Monitor closely", "Review position size", "Set price alert"],
    }
