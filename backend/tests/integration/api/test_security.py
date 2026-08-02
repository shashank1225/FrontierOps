from httpx import AsyncClient


async def test_api_responses_include_security_and_correlation_headers(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "release-check-42"},
    )

    assert response.headers["x-request-id"] == "release-check-42"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )


async def test_invalid_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "contains spaces and is invalid"},
    )

    assert response.headers["x-request-id"] != "contains spaces and is invalid"
    assert len(response.headers["x-request-id"]) == 36
