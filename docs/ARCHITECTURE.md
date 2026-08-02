# FrontierOps Architecture

## Design goals

FrontierOps separates policy from infrastructure so model providers, queue implementations, and databases can change without rewriting evaluation behavior. Dependencies point inward: HTTP and worker adapters depend on use cases; use cases depend on repository and provider contracts; domain evaluation logic has no FastAPI dependency.

## Backend boundaries

| Package | Responsibility |
|---|---|
| `api` | HTTP routes, dependency wiring, and error translation |
| `services` | Application use cases and transaction orchestration |
| `repositories` | Persistence contracts and SQLAlchemy adapters |
| `providers` | Vendor-neutral generation contracts and provider registry |
| `evaluation` | Prompt rendering, model execution, scoring, jobs, history, and gates |
| `models` | SQLAlchemy aggregates and enums |
| `schemas` | Validated transport contracts |
| `observability` | Metrics and OpenTelemetry initialization |
| `middleware` | Cross-cutting HTTP metrics, correlation, and security headers |
| `config` | Typed settings, logging, database engine, and session factory |

The FastAPI application factory is the composition root. Dependencies are constructed at the boundary and injected into routes and services. Routes never perform persistence or evaluation decisions.

## Evaluation lifecycle

1. The API validates the application and enqueues an immutable job message in Redis Streams.
2. The worker claims the message through a consumer group and marks the job running.
3. The engine loads the application, active prompt, dataset, and gate policy in one unit of work.
4. Each dataset item is rendered and sent through the provider abstraction.
5. The scorer calculates answer relevance, keyword coverage, hallucination estimate, and composite quality.
6. Case results and aggregate progress are checkpointed in PostgreSQL.
7. The release-gate evaluator approves or blocks the application using persisted aggregates.
8. The worker acknowledges the queue message only after durable completion or recorded failure.

## Failure behavior

- Provider errors become failed cases and contribute to failure rate.
- Unexpected engine failures block the release and persist a sanitized error.
- Missing prompts, datasets, or gate policies fail configuration before inference.
- Redis job state allows clients to poll queued, running, completed, and failed outcomes.
- Readiness returns HTTP 503 when PostgreSQL or Redis is unavailable.

## Extension points

Implement `LLMProvider` and register the adapter to add OpenAI, Anthropic, or Gemini. Repository protocols allow alternate persistence adapters. Metric composition and gate policies are isolated so semantic or judge-model metrics can be introduced without changing routes or workers.
