import asyncio
import base64
import json
from typing import Any

from app.config import settings
from app.utils.logger import logger

VOICE_TEMPLATE = """You are a concise financial assistant. Answer this question about a market alert in 2-3 sentences:

Alert context: {event_summary}
Ticker: {ticker}
Confidence: {confidence:.0%}
Risk factors: {risk_factors}

User question: {question}"""


async def explain(alert_payload: dict[str, Any], question: str) -> dict[str, Any]:
    """Generate voice explanation via Nova Sonic. Returns transcript + base64 audio."""
    nova_analysis = alert_payload.get("nova_analysis", {})
    context_text = VOICE_TEMPLATE.format(
        event_summary=nova_analysis.get("event_summary", "Market anomaly detected"),
        ticker=alert_payload.get("ticker", "UNKNOWN"),
        confidence=nova_analysis.get("confidence_level", 0.5),
        risk_factors=", ".join(nova_analysis.get("risk_factors", [])),
        question=question,
    )

    if settings.mock_mode:
        return _mock_response(alert_payload, question)

    try:
        from app.services.bedrock_client import get_bedrock_client

        client = get_bedrock_client()
        loop = asyncio.get_event_loop()

        def _call():
            return client.invoke_model(
                modelId=settings.bedrock_nova_sonic_model_id,
                body=json.dumps({
                    "inputText": context_text,
                    "voiceId": "Matthew",
                    "outputFormat": "mp3",
                }),
                contentType="application/json",
                accept="application/json",
            )

        response = await loop.run_in_executor(None, _call)
        body = json.loads(response["body"].read())

        audio_b64 = body.get("audioStream", "")
        transcript = body.get("inputTextCharacterCount", "")

        return {
            "transcript": context_text,
            "audio_base64": audio_b64,
            "format": "mp3",
        }
    except Exception as e:
        logger.error("nova_sonic_error", error=str(e))
        return _mock_response(alert_payload, question)


def _mock_response(alert_payload: dict, question: str) -> dict:
    nova = alert_payload.get("nova_analysis", {})
    summary = nova.get("event_summary", "A market anomaly was detected.")
    ticker = alert_payload.get("ticker", "this stock")
    transcript = (
        f"Regarding your question about {ticker}: {summary} "
        f"Key risk factors include {', '.join(nova.get('risk_factors', ['volatility'])[:2])}. "
        f"I recommend you monitor the situation closely before making any decisions."
    )
    return {
        "transcript": transcript,
        "audio_base64": "",  # no audio in mock
        "format": "mock",
    }
