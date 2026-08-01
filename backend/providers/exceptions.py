class ProviderError(Exception):
    """Base exception for stable provider-layer failures."""


class UnsupportedProviderError(ProviderError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Provider '{provider}' is not registered.")


class ProviderRequestError(ProviderError):
    """The provider rejected a valid platform request."""


class ProviderUnavailableError(ProviderError):
    """The provider could not be reached or returned a server failure."""


class ProviderTimeoutError(ProviderUnavailableError):
    """The provider exceeded the configured generation deadline."""


class ProviderResponseError(ProviderError):
    """The provider returned a response that violated its documented contract."""
