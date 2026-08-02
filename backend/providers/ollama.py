from decimal import Decimal
from time import perf_counter
from typing import Any

import httpx
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from observability.metrics import MODEL_CALLS, MODEL_LATENCY, MODEL_TOKENS
from providers.contracts import GenerationRequest, GenerationResult, GenerationUsage
from providers.exceptions import (
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

tracer = trace.get_tracer(__name__)


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
        with tracer.start_as_current_span(
            "llm.generate",
            attributes={"gen_ai.provider.name": self.name, "gen_ai.request.model": request.model},
        ) as span:
            return await self._generate(request, span)

    async def _generate(self, request: GenerationRequest, span: trace.Span) -> GenerationResult:
        started_at = perf_counter()
        try:
            response = await self._client.post("/api/generate", json=self._payload(request))
            response.raise_for_status()
        except httpx.TimeoutException as error:
            MODEL_CALLS.labels(self.name, request.model, "timeout").inc()
            raise ProviderTimeoutError("Ollama generation timed out.") from error
        except httpx.HTTPStatusError as error:
            status = "server_error" if error.response.status_code >= 500 else "request_error"
            MODEL_CALLS.labels(self.name, request.model, status).inc()
            self._raise_for_status(error)
        except httpx.RequestError as error:
            MODEL_CALLS.labels(self.name, request.model, "unavailable").inc()
            raise ProviderUnavailableError("Ollama is unavailable.") from error

        latency_ms = (perf_counter() - started_at) * 1000
        try:
            result = OllamaGenerateResponse.model_validate(response.json())
        except (ValidationError, ValueError) as error:
            MODEL_CALLS.labels(self.name, request.model, "invalid_response").inc()
            message = "Ollama returned an invalid generation response."
            raise ProviderResponseError(message) from error
        if not result.done:
            MODEL_CALLS.labels(self.name, request.model, "invalid_response").inc()
            raise ProviderResponseError("Ollama returned an incomplete non-streaming response.")

        MODEL_CALLS.labels(self.name, request.model, "success").inc()
        MODEL_LATENCY.labels(self.name, request.model).observe(latency_ms / 1000)
        MODEL_TOKENS.labels(self.name, request.model, "input").inc(result.prompt_eval_count)
        MODEL_TOKENS.labels(self.name, request.model, "output").inc(result.eval_count)
        span.set_attribute("gen_ai.usage.input_tokens", result.prompt_eval_count)
        span.set_attribute("gen_ai.usage.output_tokens", result.eval_count)
        span.set_attribute("gen_ai.response.model", result.model)

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
