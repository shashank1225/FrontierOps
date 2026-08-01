from decimal import Decimal

from evaluation.release_gates import ReleaseGateEvaluator
from models.enums import ReleaseDecision
from models.evaluation import EvaluationRun
from models.release_gate import ReleaseGatePolicy


def policy(**overrides: float | None) -> ReleaseGatePolicy:
    values: dict[str, float | None] = {
        "minimum_quality_score": 0.75,
        "maximum_latency_ms": 1000.0,
        "maximum_failure_rate": 0.05,
        "maximum_cost_usd": 1.0,
    }
    values.update(overrides)
    return ReleaseGatePolicy(**values)


def run(**overrides: object) -> EvaluationRun:
    values: dict[str, object] = {
        "average_quality_score": 0.8,
        "average_latency_ms": 900.0,
        "failure_rate": 0.05,
        "total_cost_usd": Decimal("1.0"),
    }
    values.update(overrides)
    return EvaluationRun(**values)


def test_gate_approves_values_on_inclusive_boundaries() -> None:
    result = ReleaseGateEvaluator().evaluate(run(), policy())

    assert result.decision is ReleaseDecision.APPROVED
    assert result.failures == ()


def test_gate_reports_every_failed_threshold() -> None:
    result = ReleaseGateEvaluator().evaluate(
        run(
            average_quality_score=0.5,
            average_latency_ms=1500.0,
            failure_rate=0.2,
            total_cost_usd=Decimal("2"),
        ),
        policy(),
    )

    assert result.decision is ReleaseDecision.BLOCKED
    assert {failure.metric for failure in result.failures} == {
        "average_quality_score",
        "average_latency_ms",
        "failure_rate",
        "total_cost_usd",
    }


def test_gate_fails_closed_when_required_metric_is_unavailable() -> None:
    result = ReleaseGateEvaluator().evaluate(
        run(average_quality_score=None, average_latency_ms=None), policy(maximum_cost_usd=None)
    )

    assert result.decision is ReleaseDecision.BLOCKED
    assert all(failure.reason == "metric_unavailable" for failure in result.failures)
    assert {failure.metric for failure in result.failures} == {
        "average_quality_score",
        "average_latency_ms",
    }
