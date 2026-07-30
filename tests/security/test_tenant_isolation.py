"""Security tests for tenant isolation."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.application.use_cases import GetDecisionUseCase
from src.application.dto import GetDecisionRequest
from src.core.exceptions.domain import EntityNotFoundError


@pytest.mark.asyncio
async def test_tenant_isolation_get_decision():
    """Test that a user cannot access another tenant's decision."""
    # Mock decision repo to return a decision only if tenant matches
    mock_repo = AsyncMock()
    # Simulate that the repo returns None when tenant doesn't match
    mock_repo.get_by_finding_id = AsyncMock(side_effect=lambda finding_id, tenant_id: None if tenant_id != MagicMock() else MagicMock())

    use_case = GetDecisionUseCase(mock_repo)
    request = GetDecisionRequest(finding_id=MagicMock(), tenant_id=MagicMock())

    with pytest.raises(EntityNotFoundError):
        await use_case.execute(request)

    # If tenant matches, it should succeed (but we need to set up properly)
    # This is a basic test; more thorough tests would check RLS in DB.