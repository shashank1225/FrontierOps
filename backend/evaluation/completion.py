from typing import Protocol

import structlog

from integrations.servicenow.schemas import BlockedEvaluationIncident
from integrations.servicenow.service import ServiceNowIncidentService
from models.application import AIApplication
from models.enums import IntegrationSyncStatus, ReleaseDecision
from models.evaluation import EvaluationRun
from models.prompt import PromptVersion
from reports.s3 import UploadedReport

logger = structlog.get_logger(__name__)


class ReportUploader(Protocol):
    async def upload(self, run: EvaluationRun) -> UploadedReport: ...


class MetricsPublisher(Protocol):
    async def publish_evaluation(self, run: EvaluationRun) -> None: ...
    async def publish_servicenow_failure(self) -> None: ...


class EvaluationCompletionService:
    def __init__(
        self,
        *,
        reports: ReportUploader | None = None,
        servicenow: ServiceNowIncidentService | None = None,
        metrics: MetricsPublisher | None = None,
    ) -> None:
        self._reports = reports
        self._servicenow = servicenow
        self._metrics = metrics

    async def complete(self, run: EvaluationRun, app: AIApplication, prompt: PromptVersion) -> None:
        report_access_url: str | None = None
        if self._reports is not None:
            try:
                uploaded_report = await self._reports.upload(run)
                run.report_s3_url = uploaded_report.storage_url
                report_access_url = uploaded_report.access_url
            except Exception as error:
                await logger.aerror(
                    "report_upload_failed",
                    evaluation_run_id=str(run.id),
                    error_type=type(error).__name__,
                )
        if run.release_decision is ReleaseDecision.BLOCKED and self._servicenow is not None:
            run.servicenow_sync_status = IntegrationSyncStatus.PENDING
            created = await self._servicenow.create_for_blocked_evaluation(
                BlockedEvaluationIncident(
                    application_name=app.name,
                    prompt_version=prompt.version,
                    provider=run.provider,
                    model=run.model,
                    quality_score=run.average_quality_score,
                    average_latency_ms=run.average_latency_ms,
                    failure_rate=run.failure_rate,
                    estimated_cost_usd=run.total_cost_usd,
                    failed_gate_reasons=tuple(
                        str(item.get("reason", "gate_failed")) for item in run.gate_failures
                    ),
                    evaluation_run_id=run.id,
                    timestamp=run.completed_at or run.updated_at,
                    report_url=report_access_url,
                )
            )
            if created is None:
                run.servicenow_sync_status = IntegrationSyncStatus.FAILED
                if self._metrics is not None:
                    try:
                        await self._metrics.publish_servicenow_failure()
                    except Exception as error:
                        await logger.awarning(
                            "cloudwatch_metrics_failed", error_type=type(error).__name__
                        )
            else:
                run.servicenow_sync_status = IntegrationSyncStatus.SUCCEEDED
                run.servicenow_incident_number = created.number
                run.servicenow_sys_id = created.sys_id
        if self._metrics is not None:
            try:
                await self._metrics.publish_evaluation(run)
            except Exception as error:
                await logger.awarning("cloudwatch_metrics_failed", error_type=type(error).__name__)
