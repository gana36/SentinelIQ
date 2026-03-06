import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawSignal:
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "unknown"          # "reddit" | "news" | "market" | "sec" | "mock"
    ticker: str | None = None
    raw_text: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "source": self.source,
            "ticker": self.ticker,
            "raw_text": self.raw_text,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
