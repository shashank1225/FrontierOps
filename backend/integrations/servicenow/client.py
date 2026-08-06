from typing import Protocol

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from integrations.servicenow.exceptions import ServiceNowRequestError, ServiceNowResponseError
from integrations.servicenow.schemas import ServiceNowIncident, ServiceNowIncidentCreate


class ServiceNowIncidentClient(Protocol):
    async def create_incident(self, request: ServiceNowIncidentCreate) -> ServiceNowIncident: ...


class ServiceNowClient:
    """Async ServiceNow Table API adapter with bounded exponential retries."""

    def __init__(
        self,
        *,
        instance_url: str,
        username: str,
        password: str,
        incident_table: str = "incident",
        timeout_seconds: float = 10.0,
        max_attempts: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = f"{instance_url.rstrip('/')}/api/now/table/{incident_table}"
        self._auth = httpx.BasicAuth(username, password)
        self._timeout = timeout_seconds
        self._max_attempts = max_attempts
        self._transport = transport

    async def create_incident(self, request: ServiceNowIncidentCreate) -> ServiceNowIncident:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=0.1, min=0.1, max=2),
            retry=retry_if_exception_type((httpx.TransportError, ServiceNowRequestError)),
            reraise=True,
        )
        try:
            async for attempt in retrying:
                with attempt:
                    return await self._send(request)
        except (httpx.TransportError, ServiceNowRequestError) as error:
            raise ServiceNowRequestError(
                "ServiceNow incident creation failed after retries."
            ) from error
        raise ServiceNowRequestError("ServiceNow retry loop completed unexpectedly.")

    async def _send(self, request: ServiceNowIncidentCreate) -> ServiceNowIncident:
        async with httpx.AsyncClient(
            auth=self._auth, timeout=self._timeout, transport=self._transport
        ) as client:
            response = await client.post(
                self._url,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json=request.model_dump(),
            )
        if response.status_code >= 500 or response.status_code in {408, 429}:
            raise ServiceNowRequestError(
                f"ServiceNow returned retryable HTTP {response.status_code}."
            )
        if response.is_error:
            raise ServiceNowRequestError(
                f"ServiceNow rejected the request with HTTP {response.status_code}."
            )
        try:
            payload = response.json()["result"]
            return ServiceNowIncident.model_validate(payload)
        except (KeyError, TypeError, ValueError) as error:
            raise ServiceNowResponseError(
                "ServiceNow response omitted incident identifiers."
            ) from error


class MockServiceNowClient:
    """Deterministic local adapter used only when integration is disabled."""

    async def create_incident(self, request: ServiceNowIncidentCreate) -> ServiceNowIncident:
        del request
        return ServiceNowIncident(number="MOCK0000001", sys_id="mock-servicenow-sys-id")
