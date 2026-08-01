from unittest.mock import AsyncMock

import pytest

from providers.exceptions import UnsupportedProviderError
from providers.registry import ProviderRegistry


def test_registry_resolves_provider_case_insensitively() -> None:
    provider = AsyncMock()
    provider.name = "Ollama"
    registry = ProviderRegistry()
    registry.register(provider)

    assert registry.get(" ollama ") is provider
    assert registry.names == ("ollama",)


def test_registry_rejects_duplicate_provider() -> None:
    provider = AsyncMock()
    provider.name = "ollama"
    registry = ProviderRegistry()
    registry.register(provider)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(provider)


def test_registry_reports_unsupported_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(UnsupportedProviderError, match="openai"):
        registry.get("openai")


def test_registry_rejects_blank_provider_name() -> None:
    provider = AsyncMock()
    provider.name = " "

    with pytest.raises(ValueError, match="must not be blank"):
        ProviderRegistry().register(provider)
