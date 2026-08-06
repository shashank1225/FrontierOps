import asyncio
import html
import json
from dataclasses import dataclass
from typing import Any

import structlog

from models.evaluation import EvaluationRun

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class UploadedReport:
    storage_url: str
    access_url: str


class S3EvaluationReportService:
    """Render immutable JSON/HTML reports and upload them to private S3 objects."""

    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def upload(self, run: EvaluationRun) -> UploadedReport:
        prefix = f"evaluation-reports/{run.application_id}/{run.id}"
        report = self._report(run)
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=f"{prefix}/report.json",
            Body=json.dumps(report, default=str, indent=2).encode(),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=f"{prefix}/report.html",
            Body=self._html(report).encode(),
            ContentType="text/html; charset=utf-8",
            ServerSideEncryption="AES256",
        )
        url = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": f"{prefix}/report.html"},
            ExpiresIn=86400,
        )
        storage_url = f"s3://{self._bucket}/{prefix}/report.html"
        await logger.ainfo("report_uploaded", evaluation_run_id=str(run.id), report_url=storage_url)
        return UploadedReport(storage_url=storage_url, access_url=str(url))

    @staticmethod
    def _report(run: EvaluationRun) -> dict[str, Any]:
        return {
            "evaluation_run_id": str(run.id),
            "application_id": str(run.application_id),
            "prompt_version_id": str(run.prompt_version_id),
            "provider": run.provider,
            "model": run.model,
            "status": run.status.value,
            "release_decision": run.release_decision.value,
            "quality_score": run.average_quality_score,
            "average_latency_ms": run.average_latency_ms,
            "failure_rate": run.failure_rate,
            "total_cost_usd": str(run.total_cost_usd),
            "gate_failures": run.gate_failures,
            "completed_at": run.completed_at,
            "results": [
                {
                    "dataset_item_id": str(result.dataset_item_id),
                    "succeeded": result.succeeded,
                    "response": result.response,
                    "latency_ms": result.latency_ms,
                    "quality_score": result.quality_score,
                    "cost_usd": str(result.cost_usd),
                    "error_message": result.error_message,
                }
                for result in run.results
            ],
        }

    @staticmethod
    def _html(report: dict[str, Any]) -> str:
        escaped = html.escape(json.dumps(report, default=str, indent=2))
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>FrontierOps Report</title>"
            "<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 20px}"
            "pre{background:#101827;color:#d9e2f2;padding:24px;border-radius:12px;overflow:auto}</style>"
            f"</head><body><h1>FrontierOps Evaluation Report</h1><pre>{escaped}</pre></body></html>"
        )
