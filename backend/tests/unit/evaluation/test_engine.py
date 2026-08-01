import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Self, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from evaluation.engine import EvaluationEngine
from evaluation.exceptions import EvaluationConfigurationError
from evaluation.unit_of_work import EvaluationUnitOfWork
from models.application import AIApplication
from models.dataset import EvaluationDataset
from models.enums import EvaluationRunStatus, ReleaseDecision
from models.evaluation import EvaluationRun
from providers.contracts import GenerationResult, GenerationUsage, ProviderResolver
from providers.exceptions import ProviderTimeoutError


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.applications = AsyncMock()
        self.datasets = AsyncMock()
        self.runs = AsyncMock()
        self.commit_count = 0

        async def add_run(run: EvaluationRun) -> EvaluationRun:
            run.id = uuid.uuid4()
            return run

        self.runs.add.side_effect = add_run

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def commit(self) -> None:
        self.commit_count += 1


def build_engine(unit_of_work: FakeUnitOfWork, provider: AsyncMock) -> EvaluationEngine:
    resolver = MagicMock()
    resolver.get.return_value = provider

    def factory() -> EvaluationUnitOfWork:
        return cast(EvaluationUnitOfWork, unit_of_work)

    return EvaluationEngine(
        unit_of_work_factory=factory,
        provider_resolver=cast(ProviderResolver, resolver),
        clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
    )


def configure_context(
    unit_of_work: FakeUnitOfWork,
    application: AIApplication,
    dataset: EvaluationDataset,
) -> None:
    application.evaluation_dataset_id = dataset.id
    unit_of_work.applications.get.return_value = application
    unit_of_work.datasets.get.return_value = dataset


async def test_engine_persists_successful_case_and_summary(
    application_entity: AIApplication,
    dataset_entity: EvaluationDataset,
) -> None:
    unit_of_work = FakeUnitOfWork()
    provider = AsyncMock()
    provider.generate.return_value = GenerationResult(
        provider="ollama",
        model="llama3.2",
        response="Refunds are available for 30 days.",
        usage=GenerationUsage(input_tokens=12, output_tokens=8, cost_usd=Decimal("0.002")),
        latency_ms=125.0,
        finish_reason="stop",
        provider_metadata={"total_duration_ns": 125_000_000},
    )
    configure_context(unit_of_work, application_entity, dataset_entity)

    run = await build_engine(unit_of_work, provider).run(application_entity.id)

    assert run.status is EvaluationRunStatus.COMPLETED
    assert run.release_decision is ReleaseDecision.PENDING
    assert run.successful_items == 1
    assert run.failure_rate == 0
    assert run.average_latency_ms == 125.0
    assert run.average_quality_score is not None
    assert 0 <= run.average_quality_score <= 1
    assert run.total_cost_usd == Decimal("0.002")
    assert run.results[0].input_tokens == 12
    assert run.results[0].provider_metadata == {"total_duration_ns": 125_000_000}
    assert run.results[0].quality_score is not None
    assert unit_of_work.commit_count == 3
    unit_of_work.runs.add_result.assert_awaited_once()


async def test_engine_isolates_provider_failure_per_case(
    application_entity: AIApplication,
    dataset_entity: EvaluationDataset,
) -> None:
    unit_of_work = FakeUnitOfWork()
    provider = AsyncMock()
    provider.generate.side_effect = ProviderTimeoutError("timed out")
    configure_context(unit_of_work, application_entity, dataset_entity)

    run = await build_engine(unit_of_work, provider).run(application_entity.id)

    assert run.status is EvaluationRunStatus.COMPLETED
    assert run.successful_items == 0
    assert run.failure_rate == 1
    assert run.average_latency_ms is None
    assert run.results[0].succeeded is False
    assert run.results[0].error_message == "timed out"


async def test_engine_marks_run_failed_on_unexpected_error(
    application_entity: AIApplication,
    dataset_entity: EvaluationDataset,
) -> None:
    unit_of_work = FakeUnitOfWork()
    provider = AsyncMock()
    provider.generate.side_effect = RuntimeError("secret internal detail")
    configure_context(unit_of_work, application_entity, dataset_entity)

    run = await build_engine(unit_of_work, provider).run(application_entity.id)

    assert run.status is EvaluationRunStatus.FAILED
    assert run.error_message == "Unexpected evaluation engine failure."
    assert run.results == []
    assert unit_of_work.commit_count == 2


async def test_engine_rejects_application_without_dataset(
    application_entity: AIApplication,
) -> None:
    unit_of_work = FakeUnitOfWork()
    provider = AsyncMock()
    application_entity.evaluation_dataset_id = None
    unit_of_work.applications.get.return_value = application_entity

    with pytest.raises(EvaluationConfigurationError, match="no evaluation dataset"):
        await build_engine(unit_of_work, provider).run(application_entity.id)

    unit_of_work.runs.add.assert_not_awaited()
