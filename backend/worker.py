import asyncio

import httpx
from redis.asyncio import Redis

from config.database import create_database_engine, create_session_factory
from config.logging import configure_logging
from config.settings import get_settings
from evaluation.engine import EvaluationEngine
from evaluation.redis_queue import RedisEvaluationJobQueue
from evaluation.unit_of_work import SQLAlchemyEvaluationUnitOfWorkFactory
from evaluation.worker import EvaluationWorker
from providers.ollama import OllamaProvider
from providers.registry import ProviderRegistry


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(str(settings.redis_url), decode_responses=True)
    provider_client = httpx.AsyncClient(
        base_url=str(settings.ollama_base_url).rstrip("/"),
        timeout=httpx.Timeout(settings.provider_timeout_seconds),
    )
    registry = ProviderRegistry()
    registry.register(OllamaProvider(provider_client, keep_alive=settings.ollama_keep_alive))
    evaluation_engine = EvaluationEngine(
        SQLAlchemyEvaluationUnitOfWorkFactory(session_factory), registry
    )
    worker = EvaluationWorker(RedisEvaluationJobQueue(redis), evaluation_engine)
    try:
        await worker.run_forever()
    finally:
        await provider_client.aclose()
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
