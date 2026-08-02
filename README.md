# FrontierOps

FrontierOps is an AI evaluation, deployment, and observability platform for LLM-powered applications. It is designed as a production engineering portfolio project and follows Clean Architecture boundaries.

## Foundation

This initial increment provides:

- Python 3.12 FastAPI service
- typed environment configuration
- async SQLAlchemy and PostgreSQL models
- Alembic migrations
- Redis and Ollama development dependencies
- Docker Compose orchestration
- unit and integration test foundations

## Local development

```bash
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`, with health endpoints at `/api/v1/health/live` and `/api/v1/health/ready`.

Observability endpoints:

- Prometheus metrics: `http://localhost:8000/metrics/`
- Prometheus UI: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Tempo API: `http://localhost:3200`

Grafana is provisioned with Prometheus and Tempo datasources plus a FrontierOps overview dashboard. Set `GRAFANA_ADMIN_PASSWORD` in `.env` before starting shared environments.

Run backend checks in a Python 3.12 environment:

```bash
python -m pip install -e "./backend[dev]"
make lint typecheck test
```
