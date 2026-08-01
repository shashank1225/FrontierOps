import uuid
from dataclasses import dataclass
from datetime import datetime

from models.enums import EvaluationRunStatus, ReleaseDecision


@dataclass(frozen=True, slots=True)
class EvaluationRunFilter:
    application_id: uuid.UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    model: str | None = None
    prompt_version_id: uuid.UUID | None = None
    status: EvaluationRunStatus | None = None
    release_decision: ReleaseDecision | None = None
    offset: int = 0
    limit: int = 50
