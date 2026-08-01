from decimal import Decimal

import pytest

from providers.contracts import GenerationRequest, GenerationUsage


def test_usage_calculates_total_tokens() -> None:
    usage = GenerationUsage(input_tokens=10, output_tokens=4, cost_usd=Decimal("0.01"))

    assert usage.total_tokens == 14


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"model": " "}, "model"),
        ({"prompt": " "}, "prompt"),
        ({"temperature": -0.1}, "temperature"),
        ({"max_tokens": 0}, "max_tokens"),
        ({"stop": ("",)}, "stop"),
    ],
)
def test_generation_request_rejects_invalid_values(
    overrides: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {"model": "llama3.2", "prompt": "Hello"}
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        GenerationRequest(**values)  # type: ignore[arg-type]
