import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.utils.logger import logger

_DEFAULT_EVENTS = [
    {
        "ticker": "TSLA",
        "source": "mock",
        "event_type": "earnings_beat",
        "raw_text": "$TSLA just crushed Q4 earnings! EPS beat by 30%, revenue up 25% YoY. Elon hinting at major product announcements next quarter. Bulls are going wild! 🚀",
    },
    {
        "ticker": "NVDA",
        "source": "mock",
        "event_type": "analyst_upgrade",
        "raw_text": "Breaking: Goldman Sachs upgrades $NVDA to Strong Buy with $1,200 price target. AI chip demand showing no signs of slowing as data center orders surge.",
    },
    {
        "ticker": "AAPL",
        "source": "mock",
        "event_type": "sec_filing",
        "raw_text": "Apple files 8-K with SEC disclosing significant share buyback program expansion of $90B. Tim Cook signals confidence in long-term growth trajectory.",
    },
    {
        "ticker": "SPY",
        "source": "mock",
        "event_type": "macro",
        "raw_text": "BREAKING: Fed Chair Powell signals possible rate cut at next FOMC meeting citing cooling inflation data. Markets react immediately — $SPY spiking on the news.",
    },
    {
        "ticker": "META",
        "source": "mock",
        "event_type": "product_launch",
        "raw_text": "$META launches next-gen AI assistant powered by Llama 4. Early reviews praise performance rivaling GPT-4. Ad revenue guidance raised for Q1. Stock surging after-hours.",
    },
]


async def stream(interval: int | None = None) -> AsyncIterator[RawSignal]:
    """Replays demo events in a loop. Used when MOCK_MODE=true."""
    interval = interval or settings.mock_event_interval_seconds

    # Try loading from file first
    demo_path = Path("data/demo_events.json")
    if demo_path.exists():
        events = json.loads(demo_path.read_text())
    else:
        events = _DEFAULT_EVENTS

    logger.info("mock_source_started", event_count=len(events), interval_s=interval)
    idx = 0
    while True:
        event = events[idx % len(events)]
        signal = RawSignal(
            source=event.get("source", "mock"),
            ticker=event.get("ticker"),
            raw_text=event["raw_text"],
            timestamp=datetime.utcnow(),
            metadata={"event_type": event.get("event_type", "mock")},
        )
        logger.info("mock_signal_emitted", ticker=signal.ticker, event_type=signal.metadata.get("event_type"))
        yield signal
        idx += 1
        await asyncio.sleep(interval)
