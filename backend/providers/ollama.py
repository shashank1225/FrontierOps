from decimal import Decimal
from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from providers.contracts import GenerationRequest, GenerationResult, GenerationUsage
from providers.exceptions import (
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OllamaGenerateResponse(BaseModel):
    """Validated subset of Ollama's non-streaming generate response."""

    model_config = ConfigDict(extra="ignore")

    model: str
    response: str
    done: bool
    done_reason: str | None = None
    total_duration: int | None = Field(default=None, ge=0)
    load_duration: int | None = Field(default=None, ge=0)
    prompt_eval_count: int = Field(default=0, ge=0)
    prompt_eval_duration: int | None = Field(default=None, ge=0)
    eval_count: int = Field(default=0, ge=0)
    eval_duration: int | None = Field(default=None, ge=0)


class OllamaProvider:
    """Ollama adapter implementing the provider-neutral generation port."""

    name = "ollama"

    def __init__(self, client: httpx.AsyncClient, *, keep_alive: str = "5m") -> None:
        self._client = client
        self._keep_alive = keep_alive

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        started_at = perf_counter()
        try:
            response = await self._client.post("/api/generate", json=self._payload(request))
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError("Ollama generation timed out.") from error
        except httpx.HTTPStatusError as error:
            self._raise_for_status(error)
        except httpx.RequestError as error:
            raise ProviderUnavailableError("Ollama is unavailable.") from error

        latency_ms = (perf_counter() - started_at) * 1000
        try:
            result = OllamaGenerateResponse.model_validate(response.json())
        except (ValidationError, ValueError) as error:
            message = "Ollama returned an invalid generation response."
            raise ProviderResponseError(message) from error
        if not result.done:
            raise ProviderResponseError("Ollama returned an incomplete non-streaming response.")

        return GenerationResult(
            provider=self.name,
            model=result.model,
            response=result.response,
            usage=GenerationUsage(
                input_tokens=result.prompt_eval_count,
                output_tokens=result.eval_count,
                cost_usd=Decimal("0"),
            ),
            latency_ms=latency_ms,
            finish_reason=result.done_reason,
            provider_metadata=self._metadata(result),
        )

    def _payload(self, request: GenerationRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": False,
            "keep_alive": self._keep_alive,
        }
        if request.system_prompt is not None:
            payload["system"] = request.system_prompt

        options: dict[str, Any] = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if request.seed is not None:
            options["seed"] = request.seed
        if request.stop:
            options["stop"] = list(request.stop)
        if options:
            payload["options"] = options
        return payload

    @staticmethod
    def _metadata(result: OllamaGenerateResponse) -> dict[str, int]:
        values = {
            "total_duration_ns": result.total_duration,
            "load_duration_ns": result.load_duration,
            "prompt_eval_duration_ns": result.prompt_eval_duration,
            "eval_duration_ns": result.eval_duration,
        }
        return {key: value for key, value in values.items() if value is not None}

    @staticmethod
    def _raise_for_status(error: httpx.HTTPStatusError) -> None:
        status_code = error.response.status_code
        if status_code >= 500:
            raise ProviderUnavailableError(
                f"Ollama returned server status {status_code}."
            ) from error
        message = f"Ollama rejected the request with status {status_code}."
        raise ProviderRequestError(message) from error
