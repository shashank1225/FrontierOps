from typing import Any

import boto3  # type: ignore[import-untyped]

from config.settings import Settings
from evaluation.completion import EvaluationCompletionService
from integrations.servicenow.client import (
    MockServiceNowClient,
    ServiceNowClient,
    ServiceNowIncidentClient,
)
from integrations.servicenow.exceptions import ServiceNowConfigurationError
from integrations.servicenow.service import ServiceNowIncidentService
from observability.cloudwatch import CloudWatchMetricsPublisher
from reports.s3 import S3EvaluationReportService


def build_completion_service(settings: Settings) -> EvaluationCompletionService:
    boto_options: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.s3_endpoint_url is not None:
        boto_options["endpoint_url"] = str(settings.s3_endpoint_url)
    reports = None
    if settings.s3_reports_bucket:
        reports = S3EvaluationReportService(
            boto3.client("s3", **boto_options), settings.s3_reports_bucket
        )

    if settings.servicenow_enabled:
        if not (
            settings.servicenow_instance_url
            and settings.servicenow_username
            and settings.servicenow_password
        ):
            raise ServiceNowConfigurationError(
                "ServiceNow requires instance URL, username, and password when enabled."
            )
        servicenow_client: ServiceNowIncidentClient = ServiceNowClient(
            instance_url=str(settings.servicenow_instance_url),
            username=settings.servicenow_username,
            password=settings.servicenow_password.get_secret_value(),
            incident_table=settings.servicenow_incident_table,
            timeout_seconds=settings.servicenow_timeout_seconds,
            max_attempts=settings.servicenow_max_attempts,
        )
    else:
        servicenow_client = MockServiceNowClient()

    metrics = None
    if settings.cloudwatch_metrics_enabled:
        metrics = CloudWatchMetricsPublisher(
            boto3.client("cloudwatch", region_name=settings.aws_region),
            settings.cloudwatch_namespace,
        )
    return EvaluationCompletionService(
        reports=reports,
        servicenow=ServiceNowIncidentService(servicenow_client),
        metrics=metrics,
    )
