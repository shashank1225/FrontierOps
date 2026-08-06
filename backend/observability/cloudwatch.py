import asyncio
from datetime import UTC, datetime
from typing import Any

from models.evaluation import EvaluationRun


class CloudWatchMetricsPublisher:
    def __init__(self, client: Any, namespace: str = "FrontierOps") -> None:
        self._client = client
        self._namespace = namespace

    async def publish_evaluation(self, run: EvaluationRun) -> None:
        metrics: list[dict[str, Any]] = [
            {"MetricName": "evaluation_count", "Value": 1, "Unit": "Count"},
            {
                "MetricName": "blocked_release_count",
                "Value": int(run.release_decision.value == "blocked"),
                "Unit": "Count",
            },
        ]
        if run.average_quality_score is not None:
            metrics.append(
                {"MetricName": "average_quality_score", "Value": run.average_quality_score}
            )
        if run.average_latency_ms is not None:
            metrics.append(
                {
                    "MetricName": "average_latency_ms",
                    "Value": run.average_latency_ms,
                    "Unit": "Milliseconds",
                }
            )
        await asyncio.to_thread(
            self._client.put_metric_data,
            Namespace=self._namespace,
            MetricData=[{**metric, "Timestamp": datetime.now(UTC)} for metric in metrics],
        )

    async def publish_servicenow_failure(self) -> None:
        await asyncio.to_thread(
            self._client.put_metric_data,
            Namespace=self._namespace,
            MetricData=[{"MetricName": "servicenow_failure_count", "Value": 1, "Unit": "Count"}],
        )
