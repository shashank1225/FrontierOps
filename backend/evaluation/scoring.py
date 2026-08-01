from dataclasses import dataclass

from evaluation.metrics import (
    AnswerRelevanceMetric,
    HallucinationHeuristic,
    KeywordCoverageMetric,
    MetricInput,
    weighted_average,
)


@dataclass(frozen=True, slots=True)
class EvaluationScores:
    answer_relevance: float | None
    keyword_coverage: float | None
    hallucination_score: float | None
    quality_score: float | None


class EvaluationScorer:
    """Compose deterministic metrics into a normalized quality score."""

    def __init__(self) -> None:
        self._answer_relevance = AnswerRelevanceMetric()
        self._keyword_coverage = KeywordCoverageMetric()
        self._hallucination = HallucinationHeuristic()

    def score(self, metric_input: MetricInput) -> EvaluationScores:
        relevance = self._answer_relevance.score(metric_input)
        coverage = self._keyword_coverage.score(metric_input)
        hallucination = self._hallucination.score(metric_input)
        quality = weighted_average(
            (
                (relevance, 0.5),
                (coverage, 0.3),
                (None if hallucination is None else 1 - hallucination, 0.2),
            )
        )
        return EvaluationScores(
            answer_relevance=relevance,
            keyword_coverage=coverage,
            hallucination_score=hallucination,
            quality_score=quality,
        )
