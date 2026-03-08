import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: uuid.UUID
    ticker: str
    alert_type: str
    payload: dict[str, Any]
    created_at: datetime
    delivered_at: datetime | None
    read_at: datetime | None

    model_config = {"from_attributes": True}


class ActionCard(BaseModel):
    alert_id: str
    ticker: str
    event_summary: str
    sentiment: dict[str, Any]
    anomaly: dict[str, Any]
    nova_analysis: dict[str, Any]
    similar_events: list[dict[str, Any]]
    credibility_score: float
    source_links: list[str]
    target_users: list[str]
    timestamp: str
    voice_ready: bool = True
    chart_screenshot_b64: str = ""   # base64 PNG of TradingView chart (empty = no chart)
    chart_analysis: str = ""          # Nova Lite multimodal chart pattern analysis
    sec_filing_b64: str = ""          # base64 PNG of SEC EDGAR 8-K filings snapshot
