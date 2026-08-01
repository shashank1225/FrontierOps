import uuid
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import cast

import pytest
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from evaluation.history import EvaluationRunFilter
from models.enums import EvaluationRunStatus, ReleaseDecision
from models.evaluation import EvaluationResult, EvaluationRun
from repositories.evaluations import SQLAlchemyEvaluationRunRepository


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type: JSONB, _compiler: object, **_kwargs: object) -> str:
    return "JSON"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        for model in (EvaluationRun, EvaluationResult):
            table = cast(Table, model.__table__)
            await connection.run_sync(table.create)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def test_repository_checkpoints_run_and_eager_loads_results(
    session: AsyncSession,
) -> None:
    repository = SQLAlchemyEvaluationRunRepository(session)
    run = EvaluationRun(
        application_id=uuid.uuid4(),
        prompt_version_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        provider="ollama",
        model="llama3.2",
        total_items=1,
        gate_failures=[],
    )
    await repository.add(run)
    result = EvaluationResult(
        run_id=run.id,
        dataset_item_id=uuid.uuid4(),
        response="Answer",
        succeeded=True,
        latency_ms=10.0,
        input_tokens=2,
        output_tokens=1,
        cost_usd=Decimal("0"),
        answer_relevance=0.8,
        keyword_coverage=1.0,
        hallucination_score=0.1,
        quality_score=0.88,
        provider_metadata={},
    )
    await repository.add_result(result)
    run_id = run.id
    await session.commit()
    session.expire_all()

    loaded = await repository.get(run_id)

    assert loaded is not None
    assert len(loaded.results) == 1
    assert loaded.results[0].response == "Answer"
    assert loaded.results[0].quality_score == pytest.approx(0.88)


async def test_repository_filters_and_counts_runs(session: AsyncSession) -> None:
    repository = SQLAlchemyEvaluationRunRepository(session)
    application_id = uuid.uuid4()
    for model, decision in (
        ("llama3.2", ReleaseDecision.APPROVED),
        ("mistral", ReleaseDecision.BLOCKED),
    ):
        await repository.add(
            EvaluationRun(
                application_id=application_id,
                prompt_version_id=uuid.uuid4(),
                dataset_id=uuid.uuid4(),
                provider="ollama",
                model=model,
                status=EvaluationRunStatus.COMPLETED,
                release_decision=decision,
                total_items=1,
                successful_items=1,
                total_cost_usd=Decimal("0"),
                gate_failures=[],
            )
        )
    await session.commit()

    runs, total = await repository.list_filtered(
        EvaluationRunFilter(
            application_id=application_id,
            model="llama3.2",
            status=EvaluationRunStatus.COMPLETED,
            release_decision=ReleaseDecision.APPROVED,
        )
    )

    assert total == 1
    assert [run.model for run in runs] == ["llama3.2"]
