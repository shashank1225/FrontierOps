import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient

from models.dataset import EvaluationDataset
from services.exceptions import (
    EvaluationDatasetAlreadyExistsError,
    EvaluationDatasetNotFoundError,
)


async def test_create_dataset_normalizes_cases(
    client: AsyncClient,
    evaluation_dataset_service: AsyncMock,
    dataset_entity: EvaluationDataset,
) -> None:
    evaluation_dataset_service.create.return_value = dataset_entity

    response = await client.post(
        "/api/v1/datasets",
        json={
            "name": " Support Golden Set ",
            "description": "Curated support evaluation cases",
            "items": [
                {
                    "input_text": " What is the refund period? ",
                    "expected_output": "Refunds are available within 30 days.",
                    "expected_keywords": [" refund ", "REFUND", "30 days", ""],
                    "metadata": {"category": "policy"},
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["items"][0]["metadata"] == {"category": "policy"}
    command = evaluation_dataset_service.create.await_args.args[0]
    assert command.name == "Support Golden Set"
    assert command.items[0].expected_keywords == ("refund", "30 days")


async def test_create_dataset_requires_at_least_one_case(
    client: AsyncClient, evaluation_dataset_service: AsyncMock
) -> None:
    response = await client.post(
        "/api/v1/datasets",
        json={"name": "Empty", "items": []},
    )

    assert response.status_code == 422


async def test_create_dataset_returns_conflict(
    client: AsyncClient, evaluation_dataset_service: AsyncMock
) -> None:
    evaluation_dataset_service.create.side_effect = EvaluationDatasetAlreadyExistsError("Duplicate")

    response = await client.post(
        "/api/v1/datasets",
        json={"name": "Duplicate", "items": [{"input_text": "Case"}]},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "evaluation_dataset_already_exists"


async def test_get_dataset_returns_not_found(
    client: AsyncClient, evaluation_dataset_service: AsyncMock
) -> None:
    dataset_id = uuid.uuid4()
    evaluation_dataset_service.get.side_effect = EvaluationDatasetNotFoundError(dataset_id)

    response = await client.get(f"/api/v1/datasets/{dataset_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "evaluation_dataset_not_found"
