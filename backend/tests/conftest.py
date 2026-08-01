from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_health_service
from config.settings import Settings
from main import create_app
from schemas.health import ReadinessResponse


@pytest.fixture
def app() -> FastAPI:
    settings = Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
    )
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def ready_health_service(app: FastAPI) -> AsyncMock:
    service = AsyncMock()
    service.readiness.return_value = ReadinessResponse(status="ready", database=True, redis=True)
    app.dependency_overrides[get_health_service] = lambda: service
    return service
