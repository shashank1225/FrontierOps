import uuid
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from integrations.servicenow.client import ServiceNowClient
from integrations.servicenow.exceptions import ServiceNowRequestError
from integrations.servicenow.schemas import (
    BlockedEvaluationIncident,
    ServiceNowIncident,
    ServiceNowIncidentCreate,
)
from integrations.servicenow.service import ServiceNowIncidentService


def _request() -> ServiceNowIncidentCreate:
    return ServiceNowIncidentCreate(short_description="Blocked", description="Gate failed")


@pytest.mark.asyncio
async def test_client_creates_incident_with_basic_auth() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Basic ")
        assert request.url.path == "/api/now/table/incident"
        return httpx.Response(201, json={"result": {"number": "INC001", "sys_id": "abc123"}})

    client = ServiceNowClient(
        instance_url="https://example.service-now.com",
        username="api-user",
        password="secret",
        transport=httpx.MockTransport(handler),
    )
    incident = await client.create_incident(_request())
    assert incident.number == "INC001"
    assert incident.sys_id == "abc123"


@pytest.mark.asyncio
async def test_client_retries_transient_failures() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503)
        return httpx.Response(201, json={"result": {"number": "INC002", "sys_id": "def456"}})

    client = ServiceNowClient(
        instance_url="https://example.service-now.com",
        username="api-user",
        password="secret",
        max_attempts=3,
        transport=httpx.MockTransport(handler),
    )
    assert (await client.create_incident(_request())).number == "INC002"
    assert calls == 3


@pytest.mark.asyncio
async def test_client_raises_sanitized_error_after_retries() -> None:
    client = ServiceNowClient(
        instance_url="https://example.service-now.com",
        username="api-user",
        password="super-secret",
        max_attempts=2,
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
    )
    with pytest.raises(ServiceNowRequestError, match="after retries") as raised:
        await client.create_incident(_request())
    assert "super-secret" not in str(raised.value)


@pytest.mark.asyncio
async def test_service_swallows_integration_failure() -> None:
    class FailingClient:
        async def create_incident(self, request: ServiceNowIncidentCreate) -> ServiceNowIncident:
            del request
            raise ServiceNowRequestError("offline")

    incident = BlockedEvaluationIncident(
        application_name="Claims Copilot",
        prompt_version=3,
        provider="ollama",
        model="llama3.2:3b",
        quality_score=0.41,
        average_latency_ms=900.0,
        failure_rate=0.2,
        estimated_cost_usd=Decimal("0.02"),
        failed_gate_reasons=("quality below minimum",),
        evaluation_run_id=uuid.uuid4(),
        timestamp=datetime.now(UTC),
        report_url="https://reports.example/run.json",
    )
    assert (
        await ServiceNowIncidentService(FailingClient()).create_for_blocked_evaluation(incident)
        is None
    )
