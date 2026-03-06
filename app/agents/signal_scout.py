from app.agents.base_agent import BaseAgent
from app.config import settings
from app.utils.logger import logger
from app.utils.ticker_resolver import resolve_ticker


class SignalScoutAgent(BaseAgent):
    """Agent 1: Runs sentiment + anomaly detection, resolves ticker."""

    ANOMALY_PASS_THRESHOLD = -0.05  # signals with score above this are NOT anomalous enough

    async def run(self, context: dict) -> dict:
        signal = context["signal"]

        # Resolve ticker if not already set
        if not signal.ticker:
            signal.ticker = resolve_ticker(signal.raw_text) or "UNKNOWN"
        context["ticker"] = signal.ticker

        # Sentiment analysis
        if settings.mock_mode:
            from app.ml.sentiment.mock_sentiment import mock_analyze
            sentiment = mock_analyze(signal.raw_text)
        else:
            from app.ml.sentiment.finbert_classifier import get_finbert
            sentiment = await get_finbert().analyze(signal.raw_text)
        context["sentiment"] = sentiment

        # Anomaly detection — build 5-feature vector
        # [volume_zscore, price_change_pct, sentiment_intensity, keyword_spike, novelty]
        volume_zscore = signal.metadata.get("volume_zscore", 0.0)
        price_change = abs(signal.metadata.get("change_pct", 0.0))
        sentiment_intensity = abs(sentiment["intensity"])
        keyword_spike = 1.0 if any(kw in signal.raw_text.lower() for kw in ["breaking", "surge", "crash", "soar", "plunge", "beat", "miss"]) else 0.0
        novelty = 0.5  # default; could be enhanced with dedup scoring

        features = [volume_zscore, price_change, sentiment_intensity, keyword_spike, novelty]

        if settings.mock_mode:
            from app.ml.anomaly.mock_anomaly import mock_score
            anomaly = mock_score(features)
        else:
            from app.ml.anomaly.isolation_forest import get_anomaly_detector
            anomaly = await get_anomaly_detector().score(features)
        context["anomaly"] = anomaly

        # Short-circuit: skip non-anomalous signals to reduce noise
        if not anomaly["is_anomaly"]:
            logger.info(
                "signal_not_anomalous",
                ticker=signal.ticker,
                score=anomaly["anomaly_score"],
            )
            context["passed"] = False

        logger.info(
            "signal_scout_done",
            ticker=signal.ticker,
            sentiment=sentiment["label"],
            is_anomaly=anomaly["is_anomaly"],
        )
        return context
