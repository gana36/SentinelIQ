import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.db.models import User
from app.dependencies import get_current_user
from app.ingestion.normalizer import RawSignal
from app.ingestion.pipeline import inject_signal
from app.schemas.signal import SignalInjectRequest

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/inject-signal")
async def inject_signal_endpoint(
    body: SignalInjectRequest,
    current_user: User = Depends(get_current_user),
):
    if not settings.mock_mode and settings.environment != "development":
        raise HTTPException(status_code=403, detail="Dev endpoints disabled in production")

    signal = RawSignal(
        source=body.source,
        ticker=body.ticker.upper(),
        raw_text=body.text,
        timestamp=datetime.now(timezone.utc),
        metadata={"event_type": body.event_type, **body.metadata},
    )

    if body.force:
        # Bypass orchestrator — directly dispatch a synthetic alert so chart capture + email fire
        from app.schemas.alert import (ActionCard, AnomalyData, NovaAnalysis,
                                       SentimentData)
        from app.services.alert_dispatcher import dispatch

        ticker = body.ticker.upper()
        action_card = ActionCard(
            alert_id=str(uuid.uuid4()),
            ticker=ticker,
            event_summary=body.text or f"Force-injected alert for {ticker}",
            sentiment=SentimentData(label="positive", confidence=0.9, intensity=0.8,
                                    scores={"positive": 0.9, "negative": 0.05, "neutral": 0.05}),
            anomaly=AnomalyData(is_anomaly=True, anomaly_score=0.85, threshold=0.5),
            nova_analysis=NovaAnalysis(
                event_summary=body.text or f"Force-injected test alert for {ticker}",
                affected_tickers=[ticker],
                primary_driver="manual force-inject",
                sector_impact="direct",
                confidence_level=0.95,
                risk_factors=["test signal"],
                time_horizon="intraday",
                recommended_actions=[f"Review {ticker} position"],
            ),
            similar_events=[],
            credibility_score=0.9,
            source_links=[],
            target_users=[str(current_user.id)],
            timestamp=datetime.now(timezone.utc).isoformat(),
            voice_ready=False,
        )
        await dispatch(action_card)
        return {"status": "force_dispatched", "alert_id": action_card.alert_id, "ticker": ticker}

    await inject_signal(signal)
    return {"status": "injected", "signal_id": signal.signal_id, "ticker": signal.ticker}
