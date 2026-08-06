import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from evaluation.completion import EvaluationCompletionService
from integrations.servicenow.schemas import ServiceNowIncident
from models.application import AIApplication
from models.enums import (
    DeploymentStatus,
    EvaluationRunStatus,
    IntegrationSyncStatus,
    ReleaseDecision,
)
from models.evaluation import EvaluationRun
from models.prompt import PromptVersion
from reports.s3 import UploadedReport


def entities(decision: ReleaseDecision) -> tuple[EvaluationRun, AIApplication, PromptVersion]:
    app_id = uuid.uuid4()
    prompt = PromptVersion(
        id=uuid.uuid4(), application_id=app_id, version=2, template="{input}", is_active=True
    )
    app = AIApplication(
        id=app_id,
        name="Claims AI",
        provider="ollama",
        model="llama3.2",
        deployment_status=DeploymentStatus.BLOCKED,
    )
    run = EvaluationRun(
        id=uuid.uuid4(),
        application_id=app_id,
        prompt_version_id=prompt.id,
        dataset_id=uuid.uuid4(),
        provider="ollama",
        model="llama3.2",
        status=EvaluationRunStatus.COMPLETED,
        release_decision=decision,
        deployment_status=app.deployment_status,
        servicenow_sync_status=IntegrationSyncStatus.NOT_REQUIRED,
        completed_at=datetime.now(UTC),
        total_items=1,
        successful_items=1,
        average_quality_score=0.4,
        average_latency_ms=100,
        failure_rate=0,
        total_cost_usd=Decimal("0.01"),
        gate_failures=[{"reason": "below_minimum"}],
        results=[],
    )
    return run, app, prompt


async def test_blocked_run_uploads_report_and_creates_incident() -> None:
    run, app, prompt = entities(ReleaseDecision.BLOCKED)
    reports = AsyncMock()
    reports.upload.return_value = UploadedReport(
        storage_url="s3://reports/run/report.html",
        access_url="https://reports.example/run/report.html",
    )
    servicenow = AsyncMock()
    servicenow.create_for_blocked_evaluation.return_value = ServiceNowIncident(
        number="INC1", sys_id="sys1"
    )
    await EvaluationCompletionService(reports=reports, servicenow=servicenow).complete(
        run, app, prompt
    )
    assert run.servicenow_sync_status is IntegrationSyncStatus.SUCCEEDED
    assert run.servicenow_incident_number == "INC1"
    assert run.report_s3_url == "s3://reports/run/report.html"


async def test_approved_run_does_not_create_incident() -> None:
    run, app, prompt = entities(ReleaseDecision.APPROVED)
    servicenow = AsyncMock()
    await EvaluationCompletionService(servicenow=servicenow).complete(run, app, prompt)
    servicenow.create_for_blocked_evaluation.assert_not_awaited()
    assert run.servicenow_sync_status is IntegrationSyncStatus.NOT_REQUIRED
