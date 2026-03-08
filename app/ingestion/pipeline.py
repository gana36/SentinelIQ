import asyncio

from app.config import settings
from app.ingestion.normalizer import RawSignal
from app.services.cache import push_live_signal
from app.utils.logger import logger

_pipeline_queue: asyncio.Queue[RawSignal] = None
_pipeline_task: asyncio.Task = None


def get_queue() -> asyncio.Queue[RawSignal]:
    return _pipeline_queue


async def start_pipeline() -> None:
    global _pipeline_queue, _pipeline_task
    _pipeline_queue = asyncio.Queue(maxsize=settings.signal_queue_maxsize)
    _pipeline_task = asyncio.create_task(_run())
    logger.info("ingestion_pipeline_started", mock_mode=settings.mock_mode)


async def stop_pipeline() -> None:
    if _pipeline_task:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except asyncio.CancelledError:
            pass
    logger.info("ingestion_pipeline_stopped")


async def inject_signal(signal: RawSignal) -> None:
    """Directly inject a signal into the pipeline queue (used by /dev/inject-signal)."""
    if _pipeline_queue is not None:
        await _pipeline_queue.put(signal)
        logger.info("signal_injected", ticker=signal.ticker, source=signal.source)


async def _run() -> None:
    from app.ingestion.sources import mock_source, reddit_source, news_source, market_source, sec_source, twitter_source

    producers = []

    if settings.mock_mode:
        producers.append(asyncio.create_task(_produce(mock_source.stream())))
    else:
        producers.append(asyncio.create_task(_produce(reddit_source.stream())))
        producers.append(asyncio.create_task(_produce(news_source.stream())))
        producers.append(asyncio.create_task(_produce(market_source.stream())))
        producers.append(asyncio.create_task(_produce(sec_source.stream())))
        producers.append(asyncio.create_task(_produce(twitter_source.stream())))

    consumer = asyncio.create_task(_consume())
    await asyncio.gather(*producers, consumer, return_exceptions=True)


async def _produce(source_stream) -> None:
    async for signal in source_stream:
        if _pipeline_queue is not None:
            await _pipeline_queue.put(signal)


async def _consume() -> None:
    from app.agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator()

    while True:
        signal: RawSignal = await _pipeline_queue.get()

        # Store in Redis live feed
        try:
            await push_live_signal(signal.to_dict())
        except Exception:
            pass

        # Process through agent pipeline concurrently
        asyncio.create_task(orchestrator.process(signal))
        _pipeline_queue.task_done()
