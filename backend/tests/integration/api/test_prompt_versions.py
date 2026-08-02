import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from models.prompt import PromptVersion
from services.prompt_versions import PromptVersionComparison


def prompt() -> PromptVersion:
    now = datetime(2026, 8, 2, tzinfo=UTC)
    return PromptVersion(
        id=uuid.uuid4(),
        application_id=uuid.uuid4(),
        version=2,
        template="Use the supplied context: {input}",
        change_summary="Improve grounding",
        is_active=False,
        created_at=now,
        updated_at=now,
    )


async def test_create_prompt_version_returns_next_version(
    client: AsyncClient, prompt_version_service: AsyncMock
) -> None:
    entity = prompt()
    prompt_version_service.create.return_value = entity

    response = await client.post(
        f"/api/v1/applications/{entity.application_id}/prompt-versions",
        json={"template": "Use the supplied context: {input}", "change_summary": "Improve"},
    )

    assert response.status_code == 201
    assert response.json()["version"] == 2
    prompt_version_service.create.assert_awaited_once()


async def test_create_prompt_version_rejects_unsafe_template(
    client: AsyncClient, prompt_version_service: AsyncMock
) -> None:
    response = await client.post(
        f"/api/v1/applications/{uuid.uuid4()}/prompt-versions",
        json={"template": "Use {input.__class__}"},
    )

    assert response.status_code == 422


async def test_compare_prompt_versions_returns_regression(
    client: AsyncClient, prompt_version_service: AsyncMock
) -> None:
    application_id = uuid.uuid4()
    baseline_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    prompt_version_service.compare.return_value = PromptVersionComparison(
        baseline_version_id=baseline_id,
        candidate_version_id=candidate_id,
        baseline_run_id=uuid.uuid4(),
        candidate_run_id=uuid.uuid4(),
        quality_delta=-0.1,
        latency_delta_ms=20,
        latency_delta_percent=20,
        cost_delta_usd=Decimal("0"),
        cost_delta_percent=None,
        failure_rate_delta=0,
        regression_detected=True,
        regression_reasons=("quality_decreased", "latency_increased"),
    )

    response = await client.get(
        f"/api/v1/applications/{application_id}/prompt-versions/compare"
        f"?baseline_version_id={baseline_id}&candidate_version_id={candidate_id}"
    )

    assert response.status_code == 200
    assert response.json()["regression_detected"] is True
