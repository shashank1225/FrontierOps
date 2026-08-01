import json
from collections.abc import Callable

import httpx
import pytest

from providers.contracts import GenerationRequest
from providers.exceptions import (
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from providers.ollama import OllamaProvider


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(handler),
    )


async def test_generate_maps_request_response_and_usage() -> None:
    captured_payload: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "llama3.2",
                "response": "The answer is 42.",
                "done": True,
                "done_reason": "stop",
                "total_duration": 2_000_000,
                "load_duration": 500_000,
                "prompt_eval_count": 8,
                "prompt_eval_duration": 300_000,
                "eval_count": 5,
                "eval_duration": 1_200_000,
            },
        )

    async with make_client(handler) as client:
        provider = OllamaProvider(client, keep_alive="10m")
        result = await provider.generate(
            GenerationRequest(
                model="llama3.2",
                prompt="Question",
                system_prompt="Be concise",
                temperature=0.2,
                max_tokens=100,
                seed=7,
                stop=("END",),
            )
        )

    assert captured_payload == {
        "model": "llama3.2",
        "prompt": "Question",
        "stream": False,
        "keep_alive": "10m",
        "system": "Be concise",
        "options": {
            "temperature": 0.2,
            "num_predict": 100,
            "seed": 7,
            "stop": ["END"],
        },
    }
    assert result.provider == "ollama"
    assert result.response == "The answer is 42."
    assert result.usage.input_tokens == 8
    assert result.usage.output_tokens == 5
    assert result.usage.cost_usd == 0
    assert result.provider_metadata["total_duration_ns"] == 2_000_000
    assert result.latency_ms >= 0


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [(400, ProviderRequestError), (404, ProviderRequestError), (500, ProviderUnavailableError)],
)
async def test_generate_maps_http_failures(status_code: int, error_type: type[Exception]) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "failure"})

    async with make_client(handler) as client:
        with pytest.raises(error_type):
            await OllamaProvider(client).generate(
                GenerationRequest(model="llama3.2", prompt="Question")
            )


async def test_generate_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with make_client(handler) as client:
        with pytest.raises(ProviderTimeoutError):
            await OllamaProvider(client).generate(
                GenerationRequest(model="llama3.2", prompt="Question")
            )


async def test_generate_maps_connection_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with make_client(handler) as client:
        with pytest.raises(ProviderUnavailableError):
            await OllamaProvider(client).generate(
                GenerationRequest(model="llama3.2", prompt="Question")
            )


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "llama3.2", "response": "partial", "done": False},
        {"model": "llama3.2", "done": True},
        {"model": "llama3.2", "response": "answer", "done": True, "eval_count": -1},
    ],
)
async def test_generate_rejects_invalid_response(payload: dict[str, object]) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with make_client(handler) as client:
        with pytest.raises(ProviderResponseError):
            await OllamaProvider(client).generate(
                GenerationRequest(model="llama3.2", prompt="Question")
            )
