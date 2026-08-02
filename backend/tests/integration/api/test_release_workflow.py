import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from evaluation.jobs import EvaluationJobState, EvaluationJobStatus
from models.application import AIApplication
from models.dataset import EvaluationDataset
from models.prompt import PromptVersion
from services.prompt_versions import PromptVersionComparison


async def test_application_to_release_candidate_http_workflow(
    client: AsyncClient,
    application_service: AsyncMock,
    evaluation_dataset_service: AsyncMock,
    evaluation_job_service: AsyncMock,
    prompt_version_service: AsyncMock,
    application_entity: AIApplication,
    dataset_entity: EvaluationDataset,
) -> None:
    """Exercise the public API sequence used by the dashboard release workflow."""
    application_id = application_entity.id
    dataset_id = dataset_entity.id
    assert application_entity.active_prompt_version is not None
    baseline_id = application_entity.active_prompt_version.id
    candidate_id = uuid.uuid4()
    now = datetime(2026, 8, 2, tzinfo=UTC)
    candidate = PromptVersion(
        id=candidate_id,
        application_id=application_id,
        version=2,
        template="Answer from approved context only: {input}",
        change_summary="Tighten grounding",
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    evaluation_dataset_service.create.return_value = dataset_entity
    application_service.register.return_value = application_entity
    application_entity.evaluation_dataset_id = dataset_id
    application_service.attach_evaluation_dataset.return_value = application_entity
    prompt_version_service.create.return_value = candidate
    candidate.is_active = True
    prompt_version_service.activate.return_value = candidate
    job = EvaluationJobState(
        id=uuid.uuid4(),
        application_id=application_id,
        status=EvaluationJobStatus.QUEUED,
        enqueued_at=now,
    )
    evaluation_job_service.enqueue.return_value = job
    prompt_version_service.compare.return_value = PromptVersionComparison(
        baseline_version_id=baseline_id,
        candidate_version_id=candidate_id,
        baseline_run_id=uuid.uuid4(),
        candidate_run_id=uuid.uuid4(),
        quality_delta=0.04,
        latency_delta_ms=-25,
        latency_delta_percent=-5,
        cost_delta_usd=Decimal("-0.0001"),
        cost_delta_percent=-2,
        failure_rate_delta=0,
        regression_detected=False,
        regression_reasons=(),
    )

    dataset_response = await client.post(
        "/api/v1/datasets",
        json={
            "name": "Support Golden Set",
            "items": [
                {
                    "input_text": "What is the refund period?",
                    "expected_output": "Refunds are available within 30 days.",
                    "expected_keywords": ["refund", "30 days"],
                }
            ],
        },
    )
    application_response = await client.post(
        "/api/v1/applications",
        json={
            "name": "Support Copilot",
            "provider": "ollama",
            "model": "llama3.2",
            "prompt_template": "Answer from context: {input}",
        },
    )
    attach_response = await client.put(
        f"/api/v1/applications/{application_id}/evaluation-dataset",
        json={"dataset_id": str(dataset_id)},
    )
    prompt_response = await client.post(
        f"/api/v1/applications/{application_id}/prompt-versions",
        json={"template": candidate.template, "change_summary": candidate.change_summary},
    )
    activation_response = await client.put(
        f"/api/v1/applications/{application_id}/prompt-versions/{candidate_id}/activate"
    )
    evaluation_response = await client.post(
        f"/api/v1/applications/{application_id}/evaluations"
    )
    comparison_response = await client.get(
        f"/api/v1/applications/{application_id}/prompt-versions/compare",
        params={
            "baseline_version_id": str(baseline_id),
            "candidate_version_id": str(candidate_id),
        },
    )

    assert dataset_response.status_code == 201
    assert application_response.status_code == 201
    assert attach_response.json()["evaluation_dataset_id"] == str(dataset_id)
    assert prompt_response.json()["version"] == 2
    assert activation_response.json()["is_active"] is True
    assert evaluation_response.status_code == 202
    assert evaluation_response.json()["status"] == "queued"
    assert comparison_response.status_code == 200
    assert comparison_response.json()["regression_detected"] is False
