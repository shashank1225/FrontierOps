import structlog

from integrations.servicenow.client import ServiceNowIncidentClient
from integrations.servicenow.exceptions import ServiceNowError
from integrations.servicenow.schemas import (
    BlockedEvaluationIncident,
    ServiceNowIncident,
    ServiceNowIncidentCreate,
)

logger = structlog.get_logger(__name__)


class ServiceNowIncidentService:
    """Translate domain evaluation data into ServiceNow incident requests."""

    def __init__(self, client: ServiceNowIncidentClient) -> None:
        self._client = client

    async def create_for_blocked_evaluation(
        self, incident: BlockedEvaluationIncident
    ) -> ServiceNowIncident | None:
        request = ServiceNowIncidentCreate(
            short_description=(
                f"FrontierOps blocked {incident.application_name} "
                f"v{incident.prompt_version} release"
            )[:160],
            description=incident.description(),
        )
        try:
            created = await self._client.create_incident(request)
        except ServiceNowError as error:
            await logger.awarning(
                "servicenow_sync_failed",
                evaluation_run_id=str(incident.evaluation_run_id),
                error_type=type(error).__name__,
            )
            return None
        await logger.ainfo(
            "servicenow_incident_created",
            evaluation_run_id=str(incident.evaluation_run_id),
            incident_number=created.number,
            servicenow_sys_id=created.sys_id,
        )
        return created
