import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import AIApplication
from models.enums import DeploymentStatus
from models.prompt import PromptVersion


class SQLAlchemyPromptVersionRepository:
    """Prompt persistence adapter with row-locked version allocation and activation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_next(
        self,
        application_id: uuid.UUID,
        template: str,
        change_summary: str | None,
    ) -> PromptVersion | None:
        application = await self._session.scalar(
            select(AIApplication).where(AIApplication.id == application_id).with_for_update()
        )
        if application is None:
            return None
        latest = await self._session.scalar(
            select(func.max(PromptVersion.version)).where(
                PromptVersion.application_id == application_id
            )
        )
        prompt = PromptVersion(
            application_id=application_id,
            version=(latest or 0) + 1,
            template=template,
            change_summary=change_summary,
            is_active=False,
        )
        self._session.add(prompt)
        await self._session.flush()
        return prompt

    async def get_for_application(
        self, application_id: uuid.UUID, prompt_version_id: uuid.UUID
    ) -> PromptVersion | None:
        statement = select(PromptVersion).where(
            PromptVersion.application_id == application_id,
            PromptVersion.id == prompt_version_id,
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def list_for_application(self, application_id: uuid.UUID) -> Sequence[PromptVersion]:
        statement = (
            select(PromptVersion)
            .where(PromptVersion.application_id == application_id)
            .order_by(PromptVersion.version.desc())
        )
        return (await self._session.scalars(statement)).all()

    async def activate(
        self, application_id: uuid.UUID, prompt_version_id: uuid.UUID
    ) -> PromptVersion | None:
        application = await self._session.scalar(
            select(AIApplication).where(AIApplication.id == application_id).with_for_update()
        )
        if application is None:
            return None
        prompt = await self.get_for_application(application_id, prompt_version_id)
        if prompt is None:
            return None
        await self._session.execute(
            update(PromptVersion)
            .where(PromptVersion.application_id == application_id)
            .values(is_active=False)
        )
        prompt.is_active = True
        application.active_prompt_version_id = prompt.id
        application.deployment_status = DeploymentStatus.DRAFT
        await self._session.flush()
        return prompt
