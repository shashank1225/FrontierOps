import re
from collections.abc import Iterable
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "with",
    }
)


def tokenize(value: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(value.casefold()) if token not in STOP_WORDS}


@dataclass(frozen=True, slots=True)
class MetricInput:
    input_text: str
    response: str
    expected_output: str | None
    expected_keywords: tuple[str, ...]


class AnswerRelevanceMetric:
    """Measure lexical F1 overlap with the curated expected answer."""

    def score(self, metric_input: MetricInput) -> float | None:
        if not metric_input.expected_output:
            return None
        expected = tokenize(metric_input.expected_output)
        actual = tokenize(metric_input.response)
        if not expected:
            return None
        if not actual:
            return 0.0
        overlap = len(expected & actual)
        precision = overlap / len(actual)
        recall = overlap / len(expected)
        return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


class KeywordCoverageMetric:
    """Measure the fraction of expected phrases present in the response."""

    def score(self, metric_input: MetricInput) -> float | None:
        keywords = [
            keyword.strip().casefold()
            for keyword in metric_input.expected_keywords
            if keyword.strip()
        ]
        if not keywords:
            return None
        response = metric_input.response.casefold()
        return sum(keyword in response for keyword in keywords) / len(keywords)


class HallucinationHeuristic:
    """Estimate unsupported response-token ratio against supplied reference material."""

    def score(self, metric_input: MetricInput) -> float | None:
        reference_parts: list[str] = [metric_input.input_text]
        if metric_input.expected_output:
            reference_parts.append(metric_input.expected_output)
        reference_parts.extend(metric_input.expected_keywords)
        reference_tokens = tokenize(" ".join(reference_parts))
        response_tokens = tokenize(metric_input.response)
        if not response_tokens or not reference_tokens:
            return None
        unsupported = response_tokens - reference_tokens
        return len(unsupported) / len(response_tokens)


def weighted_average(values: Iterable[tuple[float | None, float]]) -> float | None:
    available = [(value, weight) for value, weight in values if value is not None]
    if not available:
        return None
    total_weight = sum(weight for _, weight in available)
    return sum(value * weight for value, weight in available) / total_weight
