from dataclasses import dataclass

import httpx
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from sqlalchemy.ext.asyncio import AsyncEngine

from config.settings import Settings

_provider: TracerProvider | None = None
_redis_instrumented = False


@dataclass(frozen=True, slots=True)
class Telemetry:
    provider: TracerProvider | None

    @property
    def enabled(self) -> bool:
        return self.provider is not None


def configure_telemetry(settings: Settings) -> Telemetry:
    global _provider
    if not settings.telemetry_enabled:
        return Telemetry(provider=None)
    if _provider is None:
        resource = Resource.create(
            {
                "service.name": settings.service_name,
                "deployment.environment.name": settings.environment,
            }
        )
        _provider = TracerProvider(
            resource=resource,
            sampler=ParentBased(TraceIdRatioBased(settings.trace_sample_ratio)),
        )
        exporter = OTLPSpanExporter(endpoint=f"{str(settings.otlp_endpoint).rstrip('/')}/v1/traces")
        _provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(_provider)
    return Telemetry(provider=_provider)


def instrument_fastapi(app: FastAPI, telemetry: Telemetry) -> None:
    if telemetry.provider is None:
        return
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=telemetry.provider,
        excluded_urls="/api/v1/health/.*,/metrics",
    )


def instrument_runtime(
    engine: AsyncEngine,
    provider_client: httpx.AsyncClient,
    telemetry: Telemetry,
) -> None:
    global _redis_instrumented
    if telemetry.provider is None:
        return
    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine, tracer_provider=telemetry.provider
    )
    HTTPXClientInstrumentor.instrument_client(provider_client, tracer_provider=telemetry.provider)
    if not _redis_instrumented:
        RedisInstrumentor().instrument(tracer_provider=telemetry.provider)
        _redis_instrumented = True


def uninstrument_runtime(engine: AsyncEngine, provider_client: httpx.AsyncClient) -> None:
    SQLAlchemyInstrumentor().uninstrument(engine=engine.sync_engine)
    HTTPXClientInstrumentor.uninstrument_client(provider_client)
