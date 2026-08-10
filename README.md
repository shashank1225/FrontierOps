# FrontierOps

FrontierOps is an AI evaluation, deployment, and observability control plane for LLM-powered applications. It models the platform an enterprise AI team uses to register applications, test prompts against curated datasets, enforce release gates, compare versions, and investigate production signals before deployment.

This is an engineering platform, not a chatbot.

## Capabilities

- AI application registry with provider, model, prompt, dataset, and deployment state
- Provider abstraction with a production Ollama adapter
- Deterministic answer relevance, keyword coverage, and hallucination heuristics
- Asynchronous Redis-backed evaluation jobs and worker processing
- Quality, latency, failure-rate, and cost release gates
- Immutable prompt versions with activation, comparison, and regression detection
- Filterable evaluation history with persisted case-level results
- React and TypeScript operational dashboard
- OpenTelemetry traces, Prometheus metrics, Tempo, and provisioned Grafana dashboards
- Docker Compose development environment and GitHub Actions release validation
- AWS Fargate deployment with S3 reports, CloudWatch metrics, and ServiceNow incidents

## Architecture

```mermaid
flowchart LR
    UI["React operations dashboard"] --> API["FastAPI application"]
    API --> SVC["Service layer"]
    SVC --> REPO["Repository contracts"]
    REPO --> PG[(PostgreSQL)]
    API --> Q["Redis evaluation queue"]
    Q --> W["Evaluation worker"]
    W --> P["Provider registry"]
    P --> O["Ollama"]
    W --> SCORE["Metrics and release gates"]
    SCORE --> PG
    SCORE --> S3["S3 JSON and HTML reports"]
    SCORE --> SN["ServiceNow incident for blocked releases"]
    API --> OTEL["OpenTelemetry Collector"]
    W --> OTEL
    OTEL --> TEMPO["Tempo"]
    API --> PROM["Prometheus"]
    W --> PROM
    PROM --> GRAFANA["Grafana"]
    TEMPO --> GRAFANA
```

Routes contain transport concerns only. Services implement use cases, repositories isolate persistence, providers isolate model vendors, and the evaluation package owns scoring and release decisions. See [Architecture](docs/ARCHITECTURE.md) for the detailed boundaries.

## Start locally

Prerequisites: Docker Desktop and Docker Compose.

```bash
cp .env.example .env
docker compose --profile ai up --build
```

The migration container upgrades PostgreSQL before the API and worker start.

| Surface | Address |
|---|---|
| FrontierOps dashboard | http://localhost:3001 |
| API documentation | http://localhost:8000/docs |
| API health | http://localhost:8000/api/v1/health/ready |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Tempo | http://localhost:3200 |
| Ollama | http://localhost:11434 |
| LocalStack S3 | http://localhost:4566 |

Pull a local model before running evaluations:

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

Create a dataset through the API documentation, then use the dashboard to register an application and attach that dataset. Evaluations are queued through Redis and processed by the worker.

## Development checks

Python 3.12 and Node.js 22.13 or newer are required for host-based development.

```bash
python -m pip install -e "./backend[dev]"
cd frontend && npm ci && cd ..
make lint typecheck test frontend-check gate
```

The CI evaluation gate uses frozen responses and the same scorer and release-gate implementation as runtime evaluations. It exits non-zero when quality, latency, failure rate, or cost violates policy and uploads a JSON report.

## Deployment

See [Deployment guide](docs/DEPLOYMENT.md) for configuration, migrations, health probes, scaling, and rollback. See [Security](SECURITY.md) before exposing FrontierOps beyond a trusted development network.

### AWS architecture

```mermaid
flowchart TD
    USER["User or dashboard"] --> ALB["Application Load Balancer"]
    ALB --> API["ECS Fargate: FastAPI"]
    API --> RDS["RDS PostgreSQL"]
    API --> REDIS["ElastiCache Redis"]
    REDIS --> WORKER["ECS Fargate: evaluation worker"]
    WORKER --> RDS
    WORKER --> S3["Private S3 reports bucket"]
    WORKER --> CW["CloudWatch logs and metrics"]
    WORKER --> SN["ServiceNow Table API"]
    SM["Secrets Manager"] --> API
    SM --> WORKER
    GH["GitHub Actions OIDC"] --> ECR["ECR"]
    GH --> ECS["ECS deployment"]
```

#### Verified AWS S3 integration

The local worker has been validated against real Amazon S3 in `ap-south-1` using temporary AWS browser-login credentials and the AWS CLI `credential_process` flow—no long-lived access keys are stored in the repository. Evaluation run `6f35a88a-e196-473b-92f9-78f6c5442104` uploaded its generated HTML report beneath the application and run identifiers in the configured reports bucket.

| Evidence | What it demonstrates |
|---|---|
| ![FrontierOps worker reporting a successful S3 upload](docs/assets/aws/worker-report-upload.png) | The worker emitted `report_uploaded` with the real `s3://` report URI before completing the blocked evaluation. |
| ![Amazon S3 HTML evaluation report object](docs/assets/aws/s3-report-object.png) | The generated `report.html` object exists in Amazon S3 in the Mumbai region. |
| ![Amazon S3 evaluation-reports prefix](docs/assets/aws/s3-evaluation-prefix.png) | FrontierOps organizes report artifacts beneath an `evaluation-reports/` prefix. |
| ![FrontierOps reports bucket in Amazon S3](docs/assets/aws/s3-bucket-region.png) | The dedicated reports bucket exists in `ap-south-1`. |

For local development, Compose passes `AWS_PROFILE`, `AWS_DEFAULT_REGION`, and `AWS_REGION` to the API and worker and mounts the host AWS configuration read-only at `/home/frontierops/.aws`. The backend image includes AWS CLI v2 so Boto3 can execute the configured credential process. A safe read-only connectivity check is:

```bash
docker compose exec worker python -c '
import boto3, os
session = boto3.Session(profile_name=os.getenv("AWS_PROFILE", "frontierops"))
bucket = os.environ["FRONTIEROPS_S3_REPORTS_BUCKET"]
session.client("s3").head_bucket(Bucket=bucket)
print("S3 access OK:", bucket)
'
```

Production ECS tasks use scoped IAM task roles instead of mounted local profiles or static credentials.

Terraform provisions the VPC, two availability zones, ALB, ECS service, worker, encrypted RDS and Redis, private versioned S3 storage, ECR, CloudWatch, Secrets Manager, autoscaling, and least-privilege task roles.

```bash
cd infra/terraform
terraform init -backend-config="bucket=YOUR_STATE_BUCKET" -backend-config="key=frontierops/production.tfstate"
terraform plan -var="container_image=ACCOUNT.dkr.ecr.REGION.amazonaws.com/frontierops:SHA"
terraform apply
```

Populate the emitted ServiceNow secret with `instance_url`, `username`, and `password`, then apply with `-var=servicenow_enabled=true`. GitHub deployment requires repository variables for the OIDC role, region, state bucket, ECR repository, ECS cluster, and ECS service. It does not use AWS access keys.

### ServiceNow workflow

```mermaid
flowchart LR
    E["Evaluation completed"] --> G{"Release gate"}
    G -->|Approved| STORE["Persist result"]
    G -->|Blocked| REPORT["Upload reports to S3"]
    REPORT --> INCIDENT["Create ServiceNow incident"]
    INCIDENT --> IDS["Persist incident number, sys_id and sync status"]
    INCIDENT -->|Unavailable| RETRY["Mark failed for later retry; evaluation remains complete"]
```

Blocked incidents contain application, prompt, model, quality, latency, failure rate, cost, gate failures, run ID, timestamp, and the report link.

#### Verified ServiceNow integration

The following evidence was captured from a real end-to-end demo. An Ollama provider failure caused the release gate to block evaluation run `3232d1f5-1f37-493f-80d1-ac01be7ab37e`. FrontierOps then created ServiceNow incident `INC0010002` and persisted the incident number, ServiceNow `sys_id`, and successful synchronization status on the evaluation run.

| Evidence | What it demonstrates |
|---|---|
| ![ServiceNow incident INC0010002 created by FrontierOps](docs/assets/servicenow/incident-created.png) | A blocked FrontierOps release produced a real incident in ServiceNow. |
| ![FrontierOps worker events for release blocking and ServiceNow incident creation](docs/assets/servicenow/worker-integration-events.png) | Structured worker events connect the provider failure, blocked gate, report upload, and incident creation. |
| ![Evaluation API response containing persisted ServiceNow synchronization fields](docs/assets/servicenow/api-run-persistence.png) | The evaluation API persisted the incident reference and `servicenow_sync_status: succeeded`. |
| ![FrontierOps dashboard showing the blocked application release](docs/assets/servicenow/dashboard-blocked-release.png) | The dashboard reflects the same blocked deployment decision for operators. |

To enable the integration locally, place the ServiceNow settings listed below in an ignored `.env` file and recreate the API and worker. Never commit the instance password.

```bash
docker compose up -d --build --force-recreate api worker
docker compose logs -f worker
```

For a successful blocked-release demonstration, the worker should emit `release_gate_blocked`, `report_upload_completed`, and `servicenow_incident_created`. The evaluation-run response should contain a non-empty `servicenow_incident_number` and a `servicenow_sync_status` of `succeeded`.

### Environment variables

ServiceNow accepts the required unprefixed names: `SERVICENOW_ENABLED`, `SERVICENOW_INSTANCE_URL`, `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD`, and `SERVICENOW_INCIDENT_TABLE`. AWS report and metrics settings use `FRONTIEROPS_AWS_REGION`, `FRONTIEROPS_S3_REPORTS_BUCKET`, `FRONTIEROPS_S3_ENDPOINT_URL`, `FRONTIEROPS_CLOUDWATCH_METRICS_ENABLED`, and `FRONTIEROPS_CLOUDWATCH_NAMESPACE`. Local browser-login development additionally uses `AWS_PROFILE`, `AWS_DEFAULT_REGION`, and `AWS_REGION`; Compose mounts the host AWS configuration read-only for the non-root `frontierops` container user.

### Demo scenario

1. Start Compose and create an application with a deliberately high minimum quality score.
2. Run an evaluation whose answer misses required keywords.
3. Confirm the release is `BLOCKED`, the reports exist in the configured S3 bucket, and the response contains ServiceNow synchronization fields.
4. Confirm the corresponding incident appears in the configured ServiceNow test instance.

The verified screenshots above cover the dashboard decision, worker integration events, persisted API state, and ServiceNow incident. Additional portfolio evidence can include the S3 report object, Grafana traces, and the GitHub Actions run.

### Security and cost controls

Resources are private by default, S3 public access is blocked, storage is encrypted, tasks run with scoped IAM roles, credentials live in Secrets Manager, ECR scanning is enabled, and the ALB should use an ACM certificate. Restrict ingress CIDRs and CORS before production use. Cost defaults use small RDS/Redis instances, lifecycle-expire old reports and images, and keep CloudWatch logs for 30 days. Production enables Multi-AZ RDS and therefore costs more; NAT Gateway, ALB, and observability ingestion are the main fixed costs.

## Project status

The cloud and ServiceNow extension is implemented in the working tree. AWS deployment is not claimed until account-specific variables, remote state, ServiceNow credentials, DNS/TLS, and budget controls are configured by the operator.
