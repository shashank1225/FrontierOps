from unittest.mock import AsyncMock

from httpx import AsyncClient


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_delegates_to_service(
    client: AsyncClient, ready_health_service: AsyncMock
) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": True, "redis": True}
    ready_health_service.readiness.assert_awaited_once()
