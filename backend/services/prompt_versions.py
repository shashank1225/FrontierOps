import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from models.evaluation import EvaluationRun
from models.prompt import PromptVersion
from repositories.contracts import EvaluationRunRepository, PromptVersionRepository
from services.exceptions import ApplicationNotFoundError


class PromptVersionNotFoundError(Exception):
    def __init__(self, prompt_version_id: uuid.UUID) -> None:
        super().__init__(f"Prompt version '{prompt_version_id}' was not found.")


class PromptVersionEvaluationNotFoundError(Exception):
    def __init__(self, prompt_version_id: uuid.UUID) -> None:
        super().__init__(f"Prompt version '{prompt_version_id}' has no completed evaluation.")


@dataclass(frozen=True, slots=True)
class PromptVersionComparison:
    baseline_version_id: uuid.UUID
    candidate_version_id: uuid.UUID
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID
    quality_delta: float | None
    latency_delta_ms: float | None
    latency_delta_percent: float | None
    cost_delta_usd: Decimal
    cost_delta_percent: float | None
    failure_rate_delta: float | None
    regression_detected: bool
    regression_reasons: tuple[str, ...]


class PromptVersionService:
    quality_regression_tolerance = -0.02
    latency_regression_percent = 10.0
    cost_regression_percent = 10.0
    failure_rate_regression_tolerance = 0.01

    def __init__(
        self,
        prompts: PromptVersionRepository,
        runs: EvaluationRunRepository,
    ) -> None:
        self._prompts = prompts
        self._runs = runs

    async def create(
        self,
        application_id: uuid.UUID,
        template: str,
        change_summary: str | None,
    ) -> PromptVersion:
        prompt = await self._prompts.create_next(application_id, template, change_summary)
        if prompt is None:
            raise ApplicationNotFoundError(application_id)
        return prompt

    async def list(self, application_id: uuid.UUID) -> Sequence[PromptVersion]:
        return await self._prompts.list_for_application(application_id)

    async def activate(
        self, application_id: uuid.UUID, prompt_version_id: uuid.UUID
    ) -> PromptVersion:
        prompt = await self._prompts.activate(application_id, prompt_version_id)
        if prompt is None:
            raise PromptVersionNotFoundError(prompt_version_id)
        return prompt

    async def compare(
        self,
        application_id: uuid.UUID,
        baseline_version_id: uuid.UUID,
        candidate_version_id: uuid.UUID,
    ) -> PromptVersionComparison:
        baseline = await self._completed_run(application_id, baseline_version_id)
        candidate = await self._completed_run(application_id, candidate_version_id)
        quality_delta = self._difference(
            candidate.average_quality_score, baseline.average_quality_score
        )
        latency_delta = self._difference(candidate.average_latency_ms, baseline.average_latency_ms)
        failure_delta = self._difference(candidate.failure_rate, baseline.failure_rate)
        latency_percent = self._percent_change(
            candidate.average_latency_ms, baseline.average_latency_ms
        )
        cost_percent = self._percent_change(
            float(candidate.total_cost_usd), float(baseline.total_cost_usd)
        )
        reasons: list[str] = []
        if quality_delta is not None and quality_delta < self.quality_regression_tolerance:
            reasons.append("quality_decreased")
        if latency_percent is not None and latency_percent > self.latency_regression_percent:
            reasons.append("latency_increased")
        if cost_percent is not None and cost_percent > self.cost_regression_percent:
            reasons.append("cost_increased")
        if failure_delta is not None and failure_delta > self.failure_rate_regression_tolerance:
            reasons.append("failure_rate_increased")
        return PromptVersionComparison(
            baseline_version_id=baseline_version_id,
            candidate_version_id=candidate_version_id,
            baseline_run_id=baseline.id,
            candidate_run_id=candidate.id,
            quality_delta=quality_delta,
            latency_delta_ms=latency_delta,
            latency_delta_percent=latency_percent,
            cost_delta_usd=candidate.total_cost_usd - baseline.total_cost_usd,
            cost_delta_percent=cost_percent,
            failure_rate_delta=failure_delta,
            regression_detected=bool(reasons),
            regression_reasons=tuple(reasons),
        )

    async def _completed_run(
        self, application_id: uuid.UUID, prompt_version_id: uuid.UUID
    ) -> EvaluationRun:
        prompt = await self._prompts.get_for_application(application_id, prompt_version_id)
        if prompt is None:
            raise PromptVersionNotFoundError(prompt_version_id)
        run = await self._runs.get_latest_completed(application_id, prompt_version_id)
        if run is None:
            raise PromptVersionEvaluationNotFoundError(prompt_version_id)
        return run

    @staticmethod
    def _difference(candidate: float | None, baseline: float | None) -> float | None:
        if candidate is None or baseline is None:
            return None
        return candidate - baseline

    @staticmethod
    def _percent_change(candidate: float | None, baseline: float | None) -> float | None:
        if candidate is None or baseline is None or baseline == 0:
            return None
        return ((candidate - baseline) / baseline) * 100
