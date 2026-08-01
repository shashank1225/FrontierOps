import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient

from models.application import AIApplication
from services.exceptions import ApplicationAlreadyExistsError, ApplicationNotFoundError


async def test_register_application_returns_created_aggregate(
    client: AsyncClient,
    application_service: AsyncMock,
    application_entity: AIApplication,
) -> None:
    application_service.register.return_value = application_entity

    response = await client.post(
        "/api/v1/applications",
        json={
            "name": " Support Copilot ",
            "description": "Answers internal support questions",
            "provider": " ollama ",
            "model": " llama3.2 ",
            "prompt_template": " Answer using only the supplied context: {input} ",
            "prompt_change_summary": "Initial prompt",
        },
    )

    assert response.status_code == 201
    assert response.json()["deployment_status"] == "draft"
    assert response.json()["active_prompt_version"]["version"] == 1
    command = application_service.register.await_args.args[0]
    assert command.name == "Support Copilot"
    assert command.provider == "ollama"


async def test_register_application_returns_conflict(
    client: AsyncClient, application_service: AsyncMock
) -> None:
    application_service.register.side_effect = ApplicationAlreadyExistsError("Duplicate")

    response = await client.post(
        "/api/v1/applications",
        json={
            "name": "Duplicate",
            "provider": "ollama",
            "model": "llama3.2",
            "prompt_template": "{input}",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "application_already_exists"


async def test_get_unknown_application_returns_not_found(
    client: AsyncClient, application_service: AsyncMock
) -> None:
    application_id = uuid.uuid4()
    application_service.get.side_effect = ApplicationNotFoundError(application_id)

    response = await client.get(f"/api/v1/applications/{application_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "application_not_found"


async def test_list_applications_applies_pagination(
    client: AsyncClient,
    application_service: AsyncMock,
    application_entity: AIApplication,
) -> None:
    application_service.list.return_value = [application_entity]

    response = await client.get("/api/v1/applications?offset=10&limit=20")

    assert response.status_code == 200
    assert len(response.json()) == 1
    query = application_service.list.await_args.args[0]
    assert query.offset == 10
    assert query.limit == 20
