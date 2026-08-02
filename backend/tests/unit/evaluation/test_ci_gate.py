from decimal import Decimal
from pathlib import Path

from evaluation.ci_gate import (
    CIEvaluationCase,
    CIEvaluationSuite,
    CIGateThresholds,
    evaluate_suite,
    main,
)
from models.enums import ReleaseDecision


def suite(*cases: CIEvaluationCase) -> CIEvaluationSuite:
    return CIEvaluationSuite(
        name="pull-request-gate",
        provider="fixture",
        model="deterministic",
        thresholds=CIGateThresholds(
            minimum_quality_score=0.8,
            maximum_latency_ms=500,
            maximum_failure_rate=0,
            maximum_cost_usd=0.01,
        ),
        cases=cases,
    )


def passing_case() -> CIEvaluationCase:
    return CIEvaluationCase(
        name="refund-policy",
        input_text="What is the refund period?",
        expected_output="Refunds are available within 30 days.",
        expected_keywords=("refund", "30 days"),
        response="Refunds are available within 30 days.",
        latency_ms=150,
        cost_usd=Decimal("0.001"),
    )


def test_ci_gate_approves_healthy_suite() -> None:
    report = evaluate_suite(suite(passing_case()))

    assert report.decision is ReleaseDecision.APPROVED
    assert report.average_quality_score == 1
    assert report.failure_rate == 0
    assert report.failures == ()


def test_ci_gate_blocks_quality_latency_cost_and_failure_regressions() -> None:
    degraded = CIEvaluationCase(
        name="degraded-answer",
        input_text="What is the refund period?",
        expected_output="Refunds are available within 30 days.",
        expected_keywords=("refund", "30 days"),
        response="Contact the sales organization for assistance.",
        latency_ms=900,
        cost_usd=Decimal("0.02"),
    )
    failed = CIEvaluationCase(
        name="provider-failure",
        input_text="When is support available?",
        succeeded=False,
    )

    report = evaluate_suite(suite(degraded, failed))

    assert report.decision is ReleaseDecision.BLOCKED
    assert {failure.metric for failure in report.failures} == {
        "average_quality_score",
        "average_latency_ms",
        "failure_rate",
        "total_cost_usd",
    }


def test_ci_gate_exposes_per_case_results() -> None:
    report = evaluate_suite(suite(passing_case()))

    assert report.cases[0].name == "refund-policy"
    assert report.cases[0].quality_score == 1
    assert report.cases[0].cost_usd == Decimal("0.001")


def test_ci_gate_command_fails_and_persists_report_when_blocked(tmp_path: Path) -> None:
    failed_case = CIEvaluationCase(
        name="provider-failure",
        input_text="When is support available?",
        succeeded=False,
    )
    suite_path = tmp_path / "blocked-suite.json"
    report_path = tmp_path / "report.json"
    suite_path.write_text(suite(failed_case).model_dump_json(), encoding="utf-8")

    exit_code = main(["--suite", str(suite_path), "--report", str(report_path)])

    assert exit_code == 1
    assert '"decision": "blocked"' in report_path.read_text(encoding="utf-8")
