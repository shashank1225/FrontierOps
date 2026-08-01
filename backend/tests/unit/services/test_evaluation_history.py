from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock

import pytest

from evaluation.history import EvaluationRunFilter
from repositories.contracts import EvaluationRunRepository
from services.evaluation_history import (
    EvaluationHistoryService,
    InvalidEvaluationRunFilterError,
)


async def test_list_rejects_inverted_date_range() -> None:
    now = datetime(2026, 8, 1, tzinfo=UTC)
    repository = AsyncMock()
    service = EvaluationHistoryService(cast(EvaluationRunRepository, repository))

    with pytest.raises(InvalidEvaluationRunFilterError):
        await service.list(
            EvaluationRunFilter(created_from=now, created_to=now - timedelta(days=1))
        )

    repository.list_filtered.assert_not_awaited()
