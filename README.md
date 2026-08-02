# FrontierOps

FrontierOps is an AI evaluation, deployment, and observability platform for LLM-powered applications. It is designed as a production engineering portfolio project and follows Clean Architecture boundaries.

## Platform capabilities

The current platform provides:

- Python 3.12 FastAPI service
- typed environment configuration
- async SQLAlchemy and PostgreSQL models
- Alembic migrations
- Redis and Ollama development dependencies
- provider-agnostic model execution and evaluation scoring
- asynchronous evaluation jobs, history, release gates, and prompt comparison
- OpenTelemetry tracing, Prometheus metrics, Tempo, and Grafana
- responsive React and TypeScript operations dashboard
- Docker Compose orchestration
- backend and frontend quality gates in GitHub Actions

## Local development

```bash
cp .env.example .env
docker compose up --build
```

The dashboard is available at `http://localhost:3001`. The API is available at `http://localhost:8000`, with health endpoints at `/api/v1/health/live` and `/api/v1/health/ready`.

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

Run frontend checks with Node.js 22.13 or newer:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm test
```

Run the same deterministic AI release gate enforced by CI:

```bash
cd backend
python -m evaluation.ci_gate \
  --suite evaluation/ci_suite.json \
  --report artifacts/ci-evaluation-report.json
```

The command exits non-zero when quality, latency, failure-rate, or cost thresholds fail. GitHub Actions uploads the JSON report even when deployment is blocked.
