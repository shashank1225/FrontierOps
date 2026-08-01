from providers.contracts import LLMProvider
from providers.exceptions import UnsupportedProviderError


class ProviderRegistry:
    """Runtime provider resolver used by evaluation orchestration."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        key = self._normalize(provider.name)
        if not key:
            raise ValueError("Provider name must not be blank.")
        if key in self._providers:
            raise ValueError(f"Provider '{provider.name}' is already registered.")
        self._providers[key] = provider

    def get(self, name: str) -> LLMProvider:
        try:
            return self._providers[self._normalize(name)]
        except KeyError as error:
            raise UnsupportedProviderError(name) from error

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip().casefold()
