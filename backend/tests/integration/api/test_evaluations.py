import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from httpx import AsyncClient

from models.enums import EvaluationRunStatus, ReleaseDecision
from models.evaluation import EvaluationResult, EvaluationRun
from services.evaluation_history import EvaluationRunNotFoundError


def run_entity() -> EvaluationRun:
    now = datetime(2026, 8, 1, tzinfo=UTC)
    run_id = uuid.uuid4()
    result = EvaluationResult(
        id=uuid.uuid4(),
        run_id=run_id,
        dataset_item_id=uuid.uuid4(),
        response="Answer",
        succeeded=True,
        latency_ms=20,
        input_tokens=3,
        output_tokens=2,
        cost_usd=Decimal("0"),
        answer_relevance=0.9,
        keyword_coverage=1.0,
        hallucination_score=0.1,
        quality_score=0.9,
        error_message=None,
        provider_metadata={},
        created_at=now,
        updated_at=now,
    )
    return EvaluationRun(
        id=run_id,
        application_id=uuid.uuid4(),
        prompt_version_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        provider="ollama",
        model="llama3.2",
        status=EvaluationRunStatus.COMPLETED,
        release_decision=ReleaseDecision.APPROVED,
        started_at=now,
        completed_at=now,
        total_items=1,
        successful_items=1,
        average_quality_score=0.9,
        average_latency_ms=20,
        failure_rate=0,
        total_cost_usd=Decimal("0"),
        gate_failures=[],
        results=[result],
        created_at=now,
        updated_at=now,
    )


async def test_list_evaluation_runs_returns_paginated_summaries(
    client: AsyncClient, evaluation_history_service: AsyncMock
) -> None:
    run = run_entity()
    evaluation_history_service.list.return_value = ([run], 1)

    response = await client.get(
        f"/api/v1/evaluation-runs?application_id={run.application_id}"
        "&run_status=completed&release_decision=approved&limit=20"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(run.id)
    filters = evaluation_history_service.list.await_args.args[0]
    assert filters.application_id == run.application_id
    assert filters.status is EvaluationRunStatus.COMPLETED


async def test_get_evaluation_run_returns_case_results(
    client: AsyncClient, evaluation_history_service: AsyncMock
) -> None:
    run = run_entity()
    evaluation_history_service.get.return_value = run

    response = await client.get(f"/api/v1/evaluation-runs/{run.id}")

    assert response.status_code == 200
    assert response.json()["results"][0]["quality_score"] == 0.9


async def test_get_unknown_evaluation_run_returns_not_found(
    client: AsyncClient, evaluation_history_service: AsyncMock
) -> None:
    run_id = uuid.uuid4()
    evaluation_history_service.get.side_effect = EvaluationRunNotFoundError(run_id)

    response = await client.get(f"/api/v1/evaluation-runs/{run_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "evaluation_run_not_found"
