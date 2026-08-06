import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from models.enums import (
    DeploymentStatus,
    EvaluationRunStatus,
    IntegrationSyncStatus,
    ReleaseDecision,
)
from models.evaluation import EvaluationRun
from reports.s3 import S3EvaluationReportService


async def test_uploads_json_and_html_reports() -> None:
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://reports.example/report.html?signature=x"
    run = EvaluationRun(
        id=uuid.uuid4(),
        application_id=uuid.uuid4(),
        prompt_version_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        provider="ollama",
        model="llama3.2",
        status=EvaluationRunStatus.COMPLETED,
        release_decision=ReleaseDecision.BLOCKED,
        deployment_status=DeploymentStatus.BLOCKED,
        servicenow_sync_status=IntegrationSyncStatus.PENDING,
        started_at=datetime.now(UTC),
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
    uploaded = await S3EvaluationReportService(client, "reports").upload(run)
    assert uploaded.storage_url.startswith("s3://reports/")
    assert uploaded.access_url.startswith("https://reports.example/report.html")
    assert client.put_object.call_count == 2
    content_types = {call.kwargs["ContentType"] for call in client.put_object.call_args_list}
    assert content_types == {"application/json", "text/html; charset=utf-8"}
    assert all(
        call.kwargs["ServerSideEncryption"] == "AES256" for call in client.put_object.call_args_list
    )
