from collections.abc import AsyncIterator
from typing import cast

import pytest
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.application import AIApplication
from models.dataset import EvaluationDataset
from models.enums import DeploymentStatus
from models.prompt import PromptVersion
from repositories.prompts import SQLAlchemyPromptVersionRepository


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        for model in (EvaluationDataset, AIApplication, PromptVersion):
            await connection.run_sync(cast(Table, model.__table__).create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def test_repository_allocates_and_activates_next_version(
    session: AsyncSession,
) -> None:
    application = AIApplication(name="App", provider="ollama", model="llama3.2")
    session.add(application)
    await session.flush()
    first = PromptVersion(
        application_id=application.id, version=1, template="{input}", is_active=True
    )
    session.add(first)
    await session.commit()
    repository = SQLAlchemyPromptVersionRepository(session)

    second = await repository.create_next(application.id, "Context: {input}", "Grounding")

    assert second is not None
    assert second.version == 2
    assert second.is_active is False
    activated = await repository.activate(application.id, second.id)
    await session.commit()
    assert activated is not None
    assert activated.is_active is True
    assert application.deployment_status is DeploymentStatus.DRAFT
    prompts = await repository.list_for_application(application.id)
    assert [prompt.version for prompt in prompts] == [2, 1]
