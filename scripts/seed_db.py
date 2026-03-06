"""
Create a demo user with watchlist for hackathon demo.
Run: python scripts/seed_db.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import User, UserPreferences, WatchlistItem
from app.db.session import AsyncSessionLocal, engine
from app.db.base import Base
import app.db.models  # noqa: F401


DEMO_EMAIL = "demo@sentineliq.ai"
DEMO_PASSWORD = "demo1234"
DEMO_WATCHLIST = ["TSLA", "AAPL", "NVDA", "META", "SPY"]


async def seed():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if demo user exists
        result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        user = result.scalar_one_or_none()

        if user:
            print(f"Demo user already exists: {DEMO_EMAIL}")
        else:
            user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD))
            db.add(user)
            await db.flush()

            prefs = UserPreferences(
                user_id=user.id,
                risk_tolerance="medium",
                alert_sensitivity=0.3,  # Low threshold so demo events always fire
                sectors=json.dumps(["Technology", "Automotive", "Macro"]),
            )
            db.add(prefs)

            for ticker in DEMO_WATCHLIST:
                item = WatchlistItem(user_id=user.id, ticker=ticker)
                db.add(item)

            await db.commit()
            print(f"Demo user created: {DEMO_EMAIL} / {DEMO_PASSWORD}")
            print(f"Watchlist: {', '.join(DEMO_WATCHLIST)}")

        print(f"\nUser ID: {user.id}")
        print("Login via: POST /api/v1/auth/login")


if __name__ == "__main__":
    asyncio.run(seed())
