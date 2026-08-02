import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter

from opentelemetry import trace

from evaluation.exceptions import EvaluationConfigurationError, PromptRenderingError
from evaluation.metrics import MetricInput
from evaluation.prompt_renderer import PromptRenderer
from evaluation.release_gates import ReleaseGateEvaluator
from evaluation.scoring import EvaluationScorer
from evaluation.unit_of_work import EvaluationUnitOfWork, EvaluationUnitOfWorkFactory
from models.application import AIApplication
from models.dataset import EvaluationDataset, EvaluationDatasetItem
from models.enums import DeploymentStatus, EvaluationRunStatus, ReleaseDecision
from models.evaluation import EvaluationResult, EvaluationRun
from models.prompt import PromptVersion
from observability.metrics import EVALUATION_DURATION, EVALUATION_RUNS
from providers.contracts import GenerationRequest, LLMProvider, ProviderResolver
from providers.exceptions import ProviderError

tracer = trace.get_tracer(__name__)


class EvaluationEngine:
    """Execute dataset cases while checkpointing durable run progress."""

    def __init__(
        self,
        unit_of_work_factory: EvaluationUnitOfWorkFactory,
        provider_resolver: ProviderResolver,
        *,
        prompt_renderer: PromptRenderer | None = None,
        scorer: EvaluationScorer | None = None,
        release_gate_evaluator: ReleaseGateEvaluator | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._provider_resolver = provider_resolver
        self._prompt_renderer = prompt_renderer or PromptRenderer()
        self._scorer = scorer or EvaluationScorer()
        self._release_gate_evaluator = release_gate_evaluator or ReleaseGateEvaluator()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def run(self, application_id: uuid.UUID) -> EvaluationRun:
        started_at = perf_counter()
        with tracer.start_as_current_span(
            "evaluation.run", attributes={"frontierops.application.id": str(application_id)}
        ) as span:
            run = await self._run(application_id)
            span.set_attribute("frontierops.evaluation.run_id", str(run.id))
            span.set_attribute("frontierops.evaluation.status", run.status.value)
            span.set_attribute("frontierops.release.decision", run.release_decision.value)
            EVALUATION_RUNS.labels(run.status.value, run.release_decision.value).inc()
            EVALUATION_DURATION.labels(run.provider, run.model).observe(perf_counter() - started_at)
            return run

    async def _run(self, application_id: uuid.UUID) -> EvaluationRun:
        async with self._unit_of_work_factory() as unit_of_work:
            application, prompt, dataset = await self._load_context(unit_of_work, application_id)
            provider = self._provider_resolver.get(application.provider)
            self._validate_context(prompt, dataset)
            if application.release_gate_policy is None:
                raise EvaluationConfigurationError("Application has no release-gate policy.")

            run = EvaluationRun(
                application_id=application.id,
                prompt_version_id=prompt.id,
                dataset_id=dataset.id,
                provider=application.provider,
                model=application.model,
                status=EvaluationRunStatus.RUNNING,
                release_decision=ReleaseDecision.PENDING,
                started_at=self._clock(),
                total_items=len(dataset.items),
                successful_items=0,
                total_cost_usd=Decimal("0"),
                gate_failures=[],
            )
            await unit_of_work.runs.add(run)
            await unit_of_work.commit()

            for item in dataset.items:
                try:
                    with tracer.start_as_current_span(
                        "evaluation.case",
                        attributes={"frontierops.dataset_item.id": str(item.id)},
                    ):
                        result = await self._execute_case(run, prompt, item, provider)
                except Exception:
                    run.status = EvaluationRunStatus.FAILED
                    run.completed_at = self._clock()
                    run.error_message = "Unexpected evaluation engine failure."
                    run.release_decision = ReleaseDecision.BLOCKED
                    run.gate_failures = [
                        {
                            "metric": "evaluation_run",
                            "operator": "completed",
                            "threshold": 1.0,
                            "actual": 0.0,
                            "reason": "engine_failure",
                        }
                    ]
                    application.deployment_status = DeploymentStatus.BLOCKED
                    break
                run.results.append(result)
                await unit_of_work.runs.add_result(result)
                await unit_of_work.commit()
            else:
                self._complete(run)
                gate_result = self._release_gate_evaluator.evaluate(
                    run, application.release_gate_policy
                )
                run.release_decision = gate_result.decision
                run.gate_failures = [failure.as_record() for failure in gate_result.failures]
                application.deployment_status = (
                    DeploymentStatus.APPROVED
                    if gate_result.decision is ReleaseDecision.APPROVED
                    else DeploymentStatus.BLOCKED
                )

            await unit_of_work.runs.save(run)
            await unit_of_work.applications.save(application)
            await unit_of_work.commit()
            return run

    async def _load_context(
        self, unit_of_work: EvaluationUnitOfWork, application_id: uuid.UUID
    ) -> tuple[AIApplication, PromptVersion, EvaluationDataset]:
        application = await unit_of_work.applications.get(application_id)
        if application is None:
            raise EvaluationConfigurationError(f"Application '{application_id}' was not found.")
        if application.active_prompt_version is None:
            raise EvaluationConfigurationError("Application has no active prompt version.")
        if application.evaluation_dataset_id is None:
            raise EvaluationConfigurationError("Application has no evaluation dataset.")
        dataset = await unit_of_work.datasets.get(application.evaluation_dataset_id)
        if dataset is None:
            raise EvaluationConfigurationError("Application evaluation dataset was not found.")
        return application, application.active_prompt_version, dataset

    def _validate_context(self, prompt: PromptVersion, dataset: EvaluationDataset) -> None:
        if not dataset.items:
            raise EvaluationConfigurationError("Evaluation dataset has no cases.")
        try:
            self._prompt_renderer.validate(prompt.template)
        except PromptRenderingError as error:
            raise EvaluationConfigurationError(str(error)) from error

    async def _execute_case(
        self,
        run: EvaluationRun,
        prompt: PromptVersion,
        item: EvaluationDatasetItem,
        provider: LLMProvider,
    ) -> EvaluationResult:
        try:
            rendered_prompt = self._prompt_renderer.render(prompt.template, item.input_text)
            generation = await provider.generate(
                GenerationRequest(model=run.model, prompt=rendered_prompt)
            )
            scores = self._scorer.score(
                MetricInput(
                    input_text=item.input_text,
                    response=generation.response,
                    expected_output=item.expected_output,
                    expected_keywords=tuple(item.expected_keywords),
                )
            )
            return EvaluationResult(
                run_id=run.id,
                dataset_item_id=item.id,
                response=generation.response,
                succeeded=True,
                latency_ms=generation.latency_ms,
                input_tokens=generation.usage.input_tokens,
                output_tokens=generation.usage.output_tokens,
                cost_usd=generation.usage.cost_usd,
                answer_relevance=scores.answer_relevance,
                keyword_coverage=scores.keyword_coverage,
                hallucination_score=scores.hallucination_score,
                quality_score=scores.quality_score,
                provider_metadata=generation.provider_metadata,
            )
        except ProviderError as error:
            return EvaluationResult(
                run_id=run.id,
                dataset_item_id=item.id,
                succeeded=False,
                cost_usd=Decimal("0"),
                error_message=str(error)[:2000],
                provider_metadata={},
            )

    def _complete(self, run: EvaluationRun) -> None:
        successful_results = [result for result in run.results if result.succeeded]
        latencies = [
            result.latency_ms for result in successful_results if result.latency_ms is not None
        ]
        quality_scores = [
            result.quality_score
            for result in successful_results
            if result.quality_score is not None
        ]
        run.successful_items = len(successful_results)
        run.failure_rate = (run.total_items - run.successful_items) / run.total_items
        run.average_latency_ms = sum(latencies) / len(latencies) if latencies else None
        run.average_quality_score = (
            sum(quality_scores) / len(quality_scores) if quality_scores else None
        )
        run.total_cost_usd = sum(
            (result.cost_usd for result in successful_results), start=Decimal("0")
        )
        run.status = EvaluationRunStatus.COMPLETED
        run.completed_at = self._clock()
