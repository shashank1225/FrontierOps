from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from api.router import api_router
from config.database import create_database_engine, create_session_factory
from config.logging import configure_logging
from config.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory: the composition root for production and tests."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(resolved_settings)
        redis = Redis.from_url(str(resolved_settings.redis_url), decode_responses=True)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = redis
        yield
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
    app.include_router(api_router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
