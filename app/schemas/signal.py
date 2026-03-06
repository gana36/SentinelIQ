from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RawSignalSchema(BaseModel):
    signal_id: str
    source: str
    ticker: str | None
    raw_text: str
    timestamp: datetime
    metadata: dict[str, Any] = {}


class SignalInjectRequest(BaseModel):
    ticker: str
    text: str
    source: str = "mock"
    event_type: str = "custom"
    metadata: dict[str, Any] = {}
