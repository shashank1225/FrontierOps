import pytest

from config.settings import Settings


def test_settings_accept_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTIEROPS_API_PORT", "9000")

    settings = Settings()

    assert settings.api_port == 9000


def test_settings_use_versioned_api_prefix() -> None:
    assert Settings().api_prefix == "/api/v1"


def test_settings_define_bounded_provider_timeout() -> None:
    settings = Settings(provider_timeout_seconds=30)

    assert settings.provider_timeout_seconds == 30
