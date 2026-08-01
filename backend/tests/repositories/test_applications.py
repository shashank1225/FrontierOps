from collections.abc import AsyncIterator
from typing import cast

import pytest
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.application import AIApplication
from models.dataset import EvaluationDataset
from models.prompt import PromptVersion
from models.release_gate import ReleaseGatePolicy
from repositories.applications import SQLAlchemyApplicationRepository


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        for model in (EvaluationDataset, AIApplication, PromptVersion, ReleaseGatePolicy):
            table = cast(Table, model.__table__)
            await connection.run_sync(table.create)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def test_repository_persists_and_loads_application_aggregate(
    session: AsyncSession,
) -> None:
    repository = SQLAlchemyApplicationRepository(session)
    application = AIApplication(
        name="Risk Assistant",
        description=None,
        provider="ollama",
        model="llama3.2",
    )
    prompt = PromptVersion(version=1, template="Assess: {input}", is_active=True)
    application.prompt_versions.append(prompt)
    application.active_prompt_version = prompt
    application.release_gate_policy = ReleaseGatePolicy()

    await repository.add(application)
    application_id = application.id
    await session.commit()
    session.expire_all()

    loaded = await repository.get(application_id)

    assert loaded is not None
    assert loaded.active_prompt_version is not None
    assert loaded.release_gate_policy is not None
    assert loaded.active_prompt_version.version == 1
    assert loaded.release_gate_policy.minimum_quality_score == 0.75
    assert await repository.exists_by_name("Risk Assistant") is True


async def test_repository_lists_applications(session: AsyncSession) -> None:
    repository = SQLAlchemyApplicationRepository(session)
    for name in ("First", "Second"):
        application = AIApplication(name=name, provider="ollama", model="llama3.2")
        prompt = PromptVersion(version=1, template="{input}", is_active=True)
        application.prompt_versions.append(prompt)
        application.active_prompt_version = prompt
        application.release_gate_policy = ReleaseGatePolicy()
        await repository.add(application)
    await session.commit()

    applications = await repository.list(offset=0, limit=10)

    assert {application.name for application in applications} == {"First", "Second"}
