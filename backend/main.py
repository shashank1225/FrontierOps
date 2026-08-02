from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from redis.asyncio import Redis

from api.errors import register_exception_handlers
from api.router import api_router
from config.database import create_database_engine, create_session_factory
from config.logging import configure_logging
from config.settings import Settings, get_settings
from middleware.metrics import RequestMetricsMiddleware
from observability.telemetry import (
    configure_telemetry,
    instrument_fastapi,
    instrument_runtime,
    uninstrument_runtime,
)
from providers.ollama import OllamaProvider
from providers.registry import ProviderRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory: the composition root for production and tests."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    telemetry = configure_telemetry(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(resolved_settings)
        redis = Redis.from_url(str(resolved_settings.redis_url), decode_responses=True)
        provider_client = httpx.AsyncClient(
            base_url=str(resolved_settings.ollama_base_url).rstrip("/"),
            timeout=httpx.Timeout(resolved_settings.provider_timeout_seconds),
        )
        provider_registry = ProviderRegistry()
        provider_registry.register(
            OllamaProvider(provider_client, keep_alive=resolved_settings.ollama_keep_alive)
        )
        instrument_runtime(engine, provider_client, telemetry)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = redis
        app.state.provider_registry = provider_registry
        yield
        if telemetry.enabled:
            uninstrument_runtime(engine, provider_client)
        await provider_client.aclose()
        await redis.aclose()
        await engine.dispose()

    app = FastAPI(
        title="FrontierOps API",
        version="0.1.0",
        description="AI evaluation, deployment, and observability platform",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestMetricsMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=resolved_settings.api_prefix)
    app.mount("/metrics", make_asgi_app())
    instrument_fastapi(app, telemetry)
    return app


app = create_app()
