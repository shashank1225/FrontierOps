import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class BlockedEvaluationIncident(BaseModel):
    """Provider-neutral incident data emitted by a blocked release gate."""

    model_config = ConfigDict(frozen=True)

    application_name: str
    prompt_version: int
    provider: str
    model: str
    quality_score: float | None
    average_latency_ms: float | None
    failure_rate: float | None
    estimated_cost_usd: Decimal
    failed_gate_reasons: tuple[str, ...] = Field(min_length=1)
    evaluation_run_id: uuid.UUID
    timestamp: datetime
    report_url: HttpUrl | None = None

    def description(self) -> str:
        report = str(self.report_url) if self.report_url else "Report upload unavailable"
        reasons = "; ".join(self.failed_gate_reasons)
        return "\n".join(
            (
                "FrontierOps blocked an AI application release.",
                f"Application: {self.application_name}",
                f"Prompt version: v{self.prompt_version}",
                f"Provider/model: {self.provider}/{self.model}",
                f"Quality score: {self.quality_score}",
                f"Average latency (ms): {self.average_latency_ms}",
                f"Failure rate: {self.failure_rate}",
                f"Estimated cost (USD): {self.estimated_cost_usd}",
                f"Failed gates: {reasons}",
                f"Evaluation run ID: {self.evaluation_run_id}",
                f"Timestamp: {self.timestamp.isoformat()}",
                f"Report: {report}",
            )
        )


class ServiceNowIncidentCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    short_description: str
    description: str
    category: str = "software"
    impact: str = "2"
    urgency: str = "2"


class ServiceNowIncident(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: str
    sys_id: str
