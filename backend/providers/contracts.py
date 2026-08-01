from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Provider-neutral text-generation input."""

    model: str
    prompt: str
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    seed: int | None = None
    stop: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model must not be blank")
        if not self.prompt.strip():
            raise ValueError("prompt must not be blank")
        if self.temperature is not None and self.temperature < 0:
            raise ValueError("temperature must be non-negative")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if any(not value.strip() for value in self.stop):
            raise ValueError("stop sequences must not be blank")


@dataclass(frozen=True, slots=True)
class GenerationUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal = Decimal("0")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class GenerationResult:
    provider: str
    model: str
    response: str
    usage: GenerationUsage
    latency_ms: float
    finish_reason: str | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    """Port implemented by every model provider adapter."""

    @property
    def name(self) -> str: ...

    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
