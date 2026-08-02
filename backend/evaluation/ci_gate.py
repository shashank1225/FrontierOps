"""Deterministic release-gate runner for pull-request validation."""

import argparse
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from evaluation.metrics import MetricInput
from evaluation.release_gates import GateFailure, ReleaseGateEvaluator
from evaluation.scoring import EvaluationScorer
from models.enums import EvaluationRunStatus, ReleaseDecision
from models.evaluation import EvaluationRun
from models.release_gate import ReleaseGatePolicy


class CIGateThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_quality_score: float = Field(ge=0, le=1)
    maximum_latency_ms: float = Field(gt=0)
    maximum_failure_rate: float = Field(ge=0, le=1)
    maximum_cost_usd: float | None = Field(default=None, gt=0)


class CIEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    input_text: str = Field(min_length=1)
    expected_output: str | None = None
    expected_keywords: tuple[str, ...] = ()
    response: str | None = None
    succeeded: bool = True
    latency_ms: float | None = Field(default=None, ge=0)
    cost_usd: Decimal = Field(default=Decimal("0"), ge=0)

    @model_validator(mode="after")
    def require_success_payload(self) -> Self:
        if self.succeeded and (not self.response or self.latency_ms is None):
            raise ValueError("successful cases require response and latency_ms")
        return self


class CIEvaluationSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    thresholds: CIGateThresholds
    cases: tuple[CIEvaluationCase, ...] = Field(min_length=1)


class CICaseResult(BaseModel):
    name: str
    succeeded: bool
    quality_score: float | None
    latency_ms: float | None
    cost_usd: Decimal


class CIGateReport(BaseModel):
    suite: str
    decision: ReleaseDecision
    total_cases: int
    successful_cases: int
    average_quality_score: float | None
    average_latency_ms: float | None
    failure_rate: float
    total_cost_usd: Decimal
    failures: tuple[GateFailure, ...]
    cases: tuple[CICaseResult, ...]


def load_suite(path: Path) -> CIEvaluationSuite:
    return CIEvaluationSuite.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_suite(suite: CIEvaluationSuite) -> CIGateReport:
    scorer = EvaluationScorer()
    case_results: list[CICaseResult] = []
    for case in suite.cases:
        quality_score: float | None = None
        if case.succeeded and case.response is not None:
            quality_score = scorer.score(
                MetricInput(
                    input_text=case.input_text,
                    response=case.response,
                    expected_output=case.expected_output,
                    expected_keywords=case.expected_keywords,
                )
            ).quality_score
        case_results.append(
            CICaseResult(
                name=case.name,
                succeeded=case.succeeded,
                quality_score=quality_score,
                latency_ms=case.latency_ms,
                cost_usd=case.cost_usd,
            )
        )

    successful = [result for result in case_results if result.succeeded]
    qualities = [result.quality_score for result in successful if result.quality_score is not None]
    latencies = [result.latency_ms for result in successful if result.latency_ms is not None]
    total_cost = sum((result.cost_usd for result in successful), start=Decimal("0"))
    application_id = uuid.uuid4()
    run = EvaluationRun(
        application_id=application_id,
        prompt_version_id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        provider=suite.provider,
        model=suite.model,
        status=EvaluationRunStatus.COMPLETED,
        release_decision=ReleaseDecision.PENDING,
        total_items=len(case_results),
        successful_items=len(successful),
        average_quality_score=sum(qualities) / len(qualities) if qualities else None,
        average_latency_ms=sum(latencies) / len(latencies) if latencies else None,
        failure_rate=(len(case_results) - len(successful)) / len(case_results),
        total_cost_usd=total_cost,
        gate_failures=[],
    )
    policy = ReleaseGatePolicy(application_id=application_id, **suite.thresholds.model_dump())
    gate = ReleaseGateEvaluator().evaluate(run, policy)
    return CIGateReport(
        suite=suite.name,
        decision=gate.decision,
        total_cases=run.total_items,
        successful_cases=run.successful_items,
        average_quality_score=run.average_quality_score,
        average_latency_ms=run.average_latency_ms,
        failure_rate=run.failure_rate,
        total_cost_usd=run.total_cost_usd,
        failures=gate.failures,
        cases=tuple(case_results),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic FrontierOps CI gate.")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    report = evaluate_suite(load_suite(arguments.suite))
    serialized = report.model_dump_json(indent=2)
    print(serialized)
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(f"{serialized}\n", encoding="utf-8")
    if report.decision is ReleaseDecision.BLOCKED:
        print("FrontierOps release gate BLOCKED deployment.", file=sys.stderr)
        return 1
    print("FrontierOps release gate APPROVED deployment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
