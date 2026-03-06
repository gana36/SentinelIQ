"""
Embed historical events and store in FAISS index.
Run: python scripts/seed_faiss.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.ml.embeddings.faiss_store import add, save
from app.ml.embeddings.nova_embeddings import embed_text


async def seed():
    events_path = Path("data/historical_events.json")
    if not events_path.exists():
        print(f"ERROR: {events_path} not found")
        return

    events = json.loads(events_path.read_text())
    print(f"Seeding FAISS with {len(events)} historical events...")

    for i, event in enumerate(events):
        text = f"{event['ticker']}: {event['event']}"
        vec = await embed_text(text)
        add(vec, event)
        print(f"  [{i+1}/{len(events)}] {event['ticker']}: {event['event'][:60]}...")

    Path(settings.faiss_index_path).parent.mkdir(parents=True, exist_ok=True)
    save()
    print(f"FAISS index saved to {settings.faiss_index_path}")
    print(f"Metadata saved to {settings.faiss_metadata_path}")


if __name__ == "__main__":
    asyncio.run(seed())
