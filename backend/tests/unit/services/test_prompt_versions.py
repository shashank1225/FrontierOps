import uuid
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock

import pytest

from models.evaluation import EvaluationRun
from models.prompt import PromptVersion
from repositories.contracts import EvaluationRunRepository, PromptVersionRepository
from services.prompt_versions import PromptVersionService


async def test_compare_detects_multi_metric_regression() -> None:
    application_id = uuid.uuid4()
    baseline_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    prompts = AsyncMock()
    prompts.get_for_application.side_effect = [
        PromptVersion(id=baseline_id),
        PromptVersion(id=candidate_id),
    ]
    runs = AsyncMock()
    runs.get_latest_completed.side_effect = [
        EvaluationRun(
            id=uuid.uuid4(),
            average_quality_score=0.9,
            average_latency_ms=100,
            failure_rate=0.01,
            total_cost_usd=Decimal("1"),
        ),
        EvaluationRun(
            id=uuid.uuid4(),
            average_quality_score=0.8,
            average_latency_ms=125,
            failure_rate=0.05,
            total_cost_usd=Decimal("1.2"),
        ),
    ]
    service = PromptVersionService(
        cast(PromptVersionRepository, prompts), cast(EvaluationRunRepository, runs)
    )

    comparison = await service.compare(application_id, baseline_id, candidate_id)

    assert comparison.regression_detected is True
    assert set(comparison.regression_reasons) == {
        "quality_decreased",
        "latency_increased",
        "cost_increased",
        "failure_rate_increased",
    }
    assert comparison.quality_delta == pytest.approx(-0.1)
    assert comparison.latency_delta_percent == 25
    assert comparison.cost_delta_usd == Decimal("0.2")


async def test_compare_allows_improvement() -> None:
    application_id = uuid.uuid4()
    baseline_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    prompts = AsyncMock()
    prompts.get_for_application.side_effect = [
        PromptVersion(id=baseline_id),
        PromptVersion(id=candidate_id),
    ]
    runs = AsyncMock()
    runs.get_latest_completed.side_effect = [
        EvaluationRun(
            id=uuid.uuid4(),
            average_quality_score=0.8,
            average_latency_ms=100,
            failure_rate=0.02,
            total_cost_usd=Decimal("0"),
        ),
        EvaluationRun(
            id=uuid.uuid4(),
            average_quality_score=0.9,
            average_latency_ms=90,
            failure_rate=0.01,
            total_cost_usd=Decimal("0"),
        ),
    ]
    service = PromptVersionService(
        cast(PromptVersionRepository, prompts), cast(EvaluationRunRepository, runs)
    )

    comparison = await service.compare(application_id, baseline_id, candidate_id)

    assert comparison.regression_detected is False
    assert comparison.cost_delta_percent is None
