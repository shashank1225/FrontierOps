from collections.abc import AsyncIterator
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import selectinload

from evaluation.engine import EvaluationEngine
from evaluation.unit_of_work import SQLAlchemyEvaluationUnitOfWorkFactory
from models.application import AIApplication
from models.base import Base
from models.dataset import EvaluationDataset, EvaluationDatasetItem
from models.enums import DeploymentStatus, EvaluationRunStatus
from models.evaluation import EvaluationRun
from models.prompt import PromptVersion
from models.release_gate import ReleaseGatePolicy
from providers.contracts import GenerationResult, GenerationUsage, ProviderResolver


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type: JSONB, _compiler: object, **_kwargs: object) -> str:
    return "JSON"


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    yield factory
    await engine.dispose()


async def test_evaluation_persists_result_without_lazy_relationship_io(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        dataset = EvaluationDataset(name="MissingGreenlet regression", description=None)
        dataset.items.append(
            EvaluationDatasetItem(
                input_text="What is the refund period?",
                expected_output="Refunds are available within 30 days.",
                expected_keywords=["refund", "30 days"],
                metadata_={},
            )
        )
        application = AIApplication(
            name="Async evaluation regression",
            description=None,
            provider="ollama",
            model="llama3.2",
            deployment_status=DeploymentStatus.DRAFT,
            evaluation_dataset=dataset,
        )
        prompt = PromptVersion(version=1, template="Answer: {input}", is_active=True)
        application.prompt_versions.append(prompt)
        application.active_prompt_version = prompt
        application.release_gate_policy = ReleaseGatePolicy(
            minimum_quality_score=0.0,
            maximum_latency_ms=5000.0,
            maximum_failure_rate=1.0,
        )
        session.add(application)
        await session.commit()
        application_id = application.id

    provider = AsyncMock()
    provider.generate.return_value = GenerationResult(
        provider="ollama",
        model="llama3.2",
        response="Refunds are available within 30 days.",
        usage=GenerationUsage(input_tokens=8, output_tokens=7, cost_usd=Decimal("0")),
        latency_ms=50.0,
        finish_reason="stop",
        provider_metadata={},
    )
    resolver = MagicMock()
    resolver.get.return_value = provider
    engine = EvaluationEngine(
        SQLAlchemyEvaluationUnitOfWorkFactory(session_factory),
        cast(ProviderResolver, resolver),
    )

    completed = await engine.run(application_id)

    assert completed.status is EvaluationRunStatus.COMPLETED
    assert len(completed.results) == 1
    async with session_factory() as verification_session:
        statement = (
            select(EvaluationRun)
            .where(EvaluationRun.id == completed.id)
            .options(selectinload(EvaluationRun.results))
        )
        persisted = (await verification_session.scalars(statement)).one()
        assert persisted.status is EvaluationRunStatus.COMPLETED
        assert len(persisted.results) == 1
        assert persisted.results[0].response == "Refunds are available within 30 days."
