from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FRONTIEROPS_",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "frontierops-api"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://frontierops:frontierops@localhost:5432/frontierops"
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    ollama_keep_alive: str = "5m"
    provider_timeout_seconds: float = Field(default=120.0, gt=0, le=1800)
    telemetry_enabled: bool = False
    otlp_endpoint: AnyHttpUrl = AnyHttpUrl("http://localhost:4318")
    trace_sample_ratio: float = Field(default=1.0, ge=0, le=1)
    worker_metrics_port: int = Field(default=9000, ge=1, le=65535)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
        ]
    )
    database_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return one immutable configuration object per process."""

    return Settings()
