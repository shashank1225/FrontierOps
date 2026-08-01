import pytest

from evaluation.metrics import (
    AnswerRelevanceMetric,
    HallucinationHeuristic,
    KeywordCoverageMetric,
    MetricInput,
)
from evaluation.scoring import EvaluationScorer


def metric_input(**overrides: object) -> MetricInput:
    values: dict[str, object] = {
        "input_text": "Explain the refund policy",
        "response": "Refunds are available for 30 days unicorn",
        "expected_output": "Refunds are available for 30 days",
        "expected_keywords": ("refund", "30 days"),
    }
    values.update(overrides)
    return MetricInput(**values)  # type: ignore[arg-type]


def test_answer_relevance_uses_lexical_f1() -> None:
    score = AnswerRelevanceMetric().score(
        metric_input(response="refund 30 days policy", expected_output="refund 30 days")
    )

    assert score == pytest.approx(6 / 7)


def test_keyword_coverage_supports_phrases() -> None:
    score = KeywordCoverageMetric().score(metric_input(response="Refund available within 30 DAYS"))

    assert score == 1.0


def test_hallucination_estimates_unsupported_token_ratio() -> None:
    score = HallucinationHeuristic().score(metric_input())

    assert score == pytest.approx(1 / 5)


def test_composite_score_inverts_hallucination_risk() -> None:
    scores = EvaluationScorer().score(
        metric_input(response="refund 30 days unicorn", expected_output="refund 30 days")
    )

    assert scores.answer_relevance == pytest.approx(6 / 7)
    assert scores.keyword_coverage == 1.0
    assert scores.hallucination_score == pytest.approx(1 / 4)
    assert scores.quality_score == pytest.approx(123 / 140)


def test_missing_reference_metrics_are_excluded_from_weight_normalization() -> None:
    scores = EvaluationScorer().score(
        metric_input(
            input_text="context",
            response="context",
            expected_output=None,
            expected_keywords=(),
        )
    )

    assert scores.answer_relevance is None
    assert scores.keyword_coverage is None
    assert scores.hallucination_score == 0
    assert scores.quality_score == 1
