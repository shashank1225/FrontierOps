import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from evaluation.jobs import EvaluationJobStatus


class EvaluationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    status: EvaluationJobStatus
    enqueued_at: datetime
    run_id: uuid.UUID | None
    error_message: str | None
