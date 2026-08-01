from dataclasses import asdict, dataclass

from models.enums import ReleaseDecision
from models.evaluation import EvaluationRun
from models.release_gate import ReleaseGatePolicy


@dataclass(frozen=True, slots=True)
class GateFailure:
    metric: str
    operator: str
    threshold: float
    actual: float | None
    reason: str

    def as_record(self) -> dict[str, str | float | None]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReleaseGateResult:
    decision: ReleaseDecision
    failures: tuple[GateFailure, ...]


class ReleaseGateEvaluator:
    """Evaluate completed run aggregates against an application's deployment policy."""

    def evaluate(self, run: EvaluationRun, policy: ReleaseGatePolicy) -> ReleaseGateResult:
        failures: list[GateFailure] = []
        self._minimum(
            failures,
            metric="average_quality_score",
            actual=run.average_quality_score,
            threshold=policy.minimum_quality_score,
        )
        self._maximum(
            failures,
            metric="average_latency_ms",
            actual=run.average_latency_ms,
            threshold=policy.maximum_latency_ms,
        )
        self._maximum(
            failures,
            metric="failure_rate",
            actual=run.failure_rate,
            threshold=policy.maximum_failure_rate,
        )
        if policy.maximum_cost_usd is not None:
            self._maximum(
                failures,
                metric="total_cost_usd",
                actual=float(run.total_cost_usd),
                threshold=policy.maximum_cost_usd,
            )
        return ReleaseGateResult(
            decision=ReleaseDecision.BLOCKED if failures else ReleaseDecision.APPROVED,
            failures=tuple(failures),
        )

    @staticmethod
    def _minimum(
        failures: list[GateFailure],
        *,
        metric: str,
        actual: float | None,
        threshold: float,
    ) -> None:
        if actual is None:
            failures.append(
                GateFailure(
                    metric=metric,
                    operator=">=",
                    threshold=threshold,
                    actual=None,
                    reason="metric_unavailable",
                )
            )
        elif actual < threshold:
            failures.append(
                GateFailure(
                    metric=metric,
                    operator=">=",
                    threshold=threshold,
                    actual=actual,
                    reason="below_minimum",
                )
            )

    @staticmethod
    def _maximum(
        failures: list[GateFailure],
        *,
        metric: str,
        actual: float | None,
        threshold: float,
    ) -> None:
        if actual is None:
            failures.append(
                GateFailure(
                    metric=metric,
                    operator="<=",
                    threshold=threshold,
                    actual=None,
                    reason="metric_unavailable",
                )
            )
        elif actual > threshold:
            failures.append(
                GateFailure(
                    metric=metric,
                    operator="<=",
                    threshold=threshold,
                    actual=actual,
                    reason="above_maximum",
                )
            )
