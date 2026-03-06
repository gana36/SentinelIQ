from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.config import settings
from app.core.middleware import setup_cors
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────
    logger.info("startup_begin", mock_mode=settings.mock_mode, env=settings.environment)

    # Initialize Redis
    from app.services.cache import init_redis
    await init_redis()
    logger.info("redis_connected")

    # Initialize DB tables (development convenience — use alembic in production)
    if settings.environment == "development":
        from app.db.session import engine
        from app.db.base import Base
        import app.db.models  # noqa: F401 — ensure all models are imported
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db_tables_ensured")

    # Start ingestion pipeline as background task
    from app.ingestion.pipeline import start_pipeline
    await start_pipeline()

    yield  # ── Server is running ──────────────────────────────────────

    # ── Shutdown ─────────────────────────────────────────────────────
    from app.ingestion.pipeline import stop_pipeline
    from app.services.cache import close_redis
    await stop_pipeline()
    await close_redis()
    logger.info("shutdown_complete")


app = FastAPI(
    title="SentinelIQ",
    description="Autonomous Market Intelligence Assistant powered by Amazon Nova",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}
