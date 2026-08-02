from httpx import AsyncClient


async def test_prometheus_metrics_endpoint_exposes_frontierops_metrics(
    client: AsyncClient,
) -> None:
    await client.get("/api/v1/health/live")

    response = await client.get("/metrics/")

    assert response.status_code == 200
    assert "frontierops_api_requests_total" in response.text
