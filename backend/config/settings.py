from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, RedisDsn, SecretStr, field_validator
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
    servicenow_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("SERVICENOW_ENABLED", "FRONTIEROPS_SERVICENOW_ENABLED"),
    )
    servicenow_instance_url: AnyHttpUrl | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SERVICENOW_INSTANCE_URL", "FRONTIEROPS_SERVICENOW_INSTANCE_URL"
        ),
    )
    servicenow_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SERVICENOW_USERNAME", "FRONTIEROPS_SERVICENOW_USERNAME"),
    )
    servicenow_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SERVICENOW_PASSWORD", "FRONTIEROPS_SERVICENOW_PASSWORD"),
    )
    servicenow_incident_table: str = Field(
        default="incident",
        pattern=r"^[A-Za-z0-9_]+$",
        validation_alias=AliasChoices(
            "SERVICENOW_INCIDENT_TABLE", "FRONTIEROPS_SERVICENOW_INCIDENT_TABLE"
        ),
    )
    servicenow_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    servicenow_max_attempts: int = Field(default=3, ge=1, le=10)
    aws_region: str = "us-east-1"
    s3_reports_bucket: str | None = None
    s3_endpoint_url: AnyHttpUrl | None = None
    cloudwatch_metrics_enabled: bool = False
    cloudwatch_namespace: str = "FrontierOps"

    @field_validator("s3_endpoint_url", mode="before")
    @classmethod
    def empty_s3_endpoint_uses_aws_default(cls, value: object) -> object:
        """Treat a blank endpoint override as a request for the standard AWS endpoint."""
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    """Return one immutable configuration object per process."""

    return Settings()
