import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import (
    get_application_service,
    get_evaluation_dataset_service,
    get_evaluation_job_service,
    get_health_service,
)
from config.settings import Settings
from main import create_app
from models.application import AIApplication
from models.dataset import EvaluationDataset, EvaluationDatasetItem
from models.enums import DeploymentStatus
from models.prompt import PromptVersion
from models.release_gate import ReleaseGatePolicy
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


@pytest.fixture
def application_entity() -> AIApplication:
    now = datetime.now(UTC)
    application_id = uuid.uuid4()
    prompt = PromptVersion(
        id=uuid.uuid4(),
        application_id=application_id,
        version=1,
        template="Answer using only the supplied context: {input}",
        change_summary="Initial prompt",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    policy = ReleaseGatePolicy(
        id=uuid.uuid4(),
        application_id=application_id,
        minimum_quality_score=0.75,
        maximum_latency_ms=5000.0,
        maximum_failure_rate=0.05,
        maximum_cost_usd=None,
        created_at=now,
        updated_at=now,
    )
    return AIApplication(
        id=application_id,
        name="Support Copilot",
        description="Answers internal support questions",
        provider="ollama",
        model="llama3.2",
        deployment_status=DeploymentStatus.DRAFT,
        evaluation_dataset_id=None,
        active_prompt_version=prompt,
        release_gate_policy=policy,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def application_service(app: FastAPI) -> AsyncMock:
    service = AsyncMock()
    app.dependency_overrides[get_application_service] = lambda: service
    return service


@pytest.fixture
def dataset_entity() -> EvaluationDataset:
    now = datetime.now(UTC)
    dataset_id = uuid.uuid4()
    item = EvaluationDatasetItem(
        id=uuid.uuid4(),
        dataset_id=dataset_id,
        input_text="What is the refund period?",
        expected_output="Refunds are available within 30 days.",
        expected_keywords=["30 days", "refund"],
        metadata_={"category": "policy"},
        created_at=now,
        updated_at=now,
    )
    return EvaluationDataset(
        id=dataset_id,
        name="Support Golden Set",
        description="Curated support evaluation cases",
        items=[item],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def evaluation_dataset_service(app: FastAPI) -> AsyncMock:
    service = AsyncMock()
    app.dependency_overrides[get_evaluation_dataset_service] = lambda: service
    return service


@pytest.fixture
def evaluation_job_service(app: FastAPI) -> AsyncMock:
    service = AsyncMock()
    app.dependency_overrides[get_evaluation_job_service] = lambda: service
    return service
