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
    await inject_signal(signal)
    return {"status": "injected", "signal_id": signal.signal_id, "ticker": signal.ticker}
