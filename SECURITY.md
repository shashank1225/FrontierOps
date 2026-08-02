# Security Policy

## Supported version

FrontierOps 1.x receives security fixes in this portfolio repository.

## Deployment posture

The included Compose environment is intended for trusted local development. It uses example PostgreSQL, Grafana, and Redis settings and must not be exposed directly to the internet.

Before production use:

- place the API and dashboard behind authenticated TLS ingress;
- replace all example credentials and use a secret manager;
- restrict CORS to approved dashboard origins;
- keep PostgreSQL, Redis, Ollama, Tempo, and Prometheus on private networks;
- disable public API documentation when organizational policy requires it;
- apply network egress controls to model providers;
- define dataset retention and redaction policies for prompts and model responses;
- review OpenTelemetry attributes before exporting traces outside the trust boundary.

The API emits request IDs and defensive browser headers, uses validated schemas, avoids returning raw provider failures, and runs containers as unprivileged users. Authentication and organization-level authorization are deployment integrations and are not supplied by the local portfolio environment.

## Reporting

Do not open public issues containing secrets, prompts, evaluation datasets, or exploit details. Report suspected vulnerabilities privately to the repository owner through GitHub's private vulnerability reporting feature.
