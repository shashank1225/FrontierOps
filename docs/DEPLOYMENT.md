# Deployment Guide

## Configuration

Copy `.env.example` and replace all development credentials. Production deployments should provide secrets through the target platform rather than committed environment files.

Required infrastructure:

- PostgreSQL 17 or a compatible managed PostgreSQL service
- Redis 7 with persistence appropriate to the recovery objective
- Ollama or another implemented provider endpoint
- OTLP-compatible collector when telemetry is enabled

The included Terraform configuration provisions AWS ALB, ECS Fargate API and worker containers, ECR, RDS PostgreSQL, ElastiCache Redis, S3, CloudWatch, IAM, and Secrets Manager. ServiceNow is external and accessed over its Table API.

Set `FRONTIEROPS_ENVIRONMENT=production`, restrict `FRONTIEROPS_CORS_ORIGINS` to trusted dashboard origins, and use TLS at the ingress or load balancer.

## Migrations

Run exactly one migration task before rolling out API and worker replicas:

```bash
cd backend
alembic upgrade head
```

Docker Compose models this with the `migrate` service. API and worker containers start only after it exits successfully. Never run concurrent schema upgrades from every application replica.

## Health and traffic

- `/api/v1/health/live` proves the API process can serve requests.
- `/api/v1/health/ready` verifies PostgreSQL and Redis and returns HTTP 503 on failure.
- `/metrics/` exposes API Prometheus metrics.
- Worker Prometheus metrics are exposed on `FRONTIEROPS_WORKER_METRICS_PORT`.

Use readiness for load-balancer registration and liveness for process replacement. Allow a startup grace period for migrations and connection establishment.

## Scaling

API replicas are stateless and may scale horizontally. Worker replicas use Redis consumer groups; give each replica a unique hostname or consumer identity. Scale workers based on queue depth and provider capacity. PostgreSQL connection limits and Ollama concurrency must be sized before increasing replicas.

## Release procedure

1. Run backend lint, typing, tests, and the deterministic evaluation gate.
2. Run frontend lint, typing, server-render test, and production build.
3. Build immutable images tagged with the commit SHA.
4. Back up PostgreSQL and execute migrations once.
5. Roll out API and workers, then wait for readiness.
6. Run a representative evaluation and verify traces, metrics, and gate results.
7. Roll out the dashboard.

GitHub Actions performs steps 1–3, verifies migrations against PostgreSQL, and prevents image builds when any prerequisite fails.

The deployment workflow authenticates with GitHub OIDC, pushes an immutable commit-SHA image to ECR, applies Terraform, runs `alembic upgrade head` as a one-off Fargate task, forces a fresh service deployment, and waits for ECS stability. Configure GitHub environment protection for production.

## Rollback

Roll back application images to the previous commit SHA. Database downgrades require an explicitly reviewed Alembic downgrade and a verified backup; do not automatically downgrade schemas during application rollback. Preserve Redis and PostgreSQL volumes during routine image rollback.
