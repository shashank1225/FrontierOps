from enum import StrEnum


class DeploymentStatus(StrEnum):
    DRAFT = "draft"
    EVALUATING = "evaluating"
    APPROVED = "approved"
    BLOCKED = "blocked"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


class EvaluationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReleaseDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"


class IntegrationSyncStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
