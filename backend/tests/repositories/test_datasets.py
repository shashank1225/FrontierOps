from collections.abc import AsyncIterator
from typing import cast

import pytest
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from models.dataset import EvaluationDataset, EvaluationDatasetItem
from repositories.datasets import SQLAlchemyEvaluationDatasetRepository


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type: JSONB, _compiler: object, **_kwargs: object) -> str:
    return "JSON"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        for model in (EvaluationDataset, EvaluationDatasetItem):
            table = cast(Table, model.__table__)
            await connection.run_sync(table.create)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def test_repository_persists_dataset_with_items(session: AsyncSession) -> None:
    repository = SQLAlchemyEvaluationDatasetRepository(session)
    dataset = EvaluationDataset(name="Golden Set", description=None)
    dataset.items.append(
        EvaluationDatasetItem(
            input_text="Question",
            expected_output="Answer",
            expected_keywords=["answer"],
            metadata_={"source": "curated"},
        )
    )

    await repository.add(dataset)
    dataset_id = dataset.id
    await session.commit()
    session.expire_all()

    loaded = await repository.get(dataset_id)

    assert loaded is not None
    assert loaded.items[0].metadata_ == {"source": "curated"}
    assert await repository.exists_by_name("Golden Set") is True


async def test_repository_lists_datasets_with_items(session: AsyncSession) -> None:
    repository = SQLAlchemyEvaluationDatasetRepository(session)
    for name in ("First", "Second"):
        dataset = EvaluationDataset(name=name)
        dataset.items.append(EvaluationDatasetItem(input_text="Case"))
        await repository.add(dataset)
    await session.commit()

    datasets = await repository.list(offset=0, limit=10)

    assert {dataset.name for dataset in datasets} == {"First", "Second"}
    assert all(len(dataset.items) == 1 for dataset in datasets)
