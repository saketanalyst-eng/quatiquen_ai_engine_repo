"""End-to-end tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from src.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_readiness_endpoint(client):
    """Test readiness endpoint."""
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200


def test_calculate_risk_endpoint(client, monkeypatch):
    """Test risk calculation endpoint."""
    # Mock use case to avoid external calls
    from src.application.use_cases import EvaluateFindingUseCase
    from src.interfaces.dependencies.inject import get_evaluate_finding_use_case

    mock_use_case = MagicMock()
    mock_use_case.execute = AsyncMock(return_value=MagicMock(
        finding_id=uuid4(),
        tenant_id=uuid4(),
        bis=85.0,
        tier="Critical",
        confidence=0.9,
        drivers={"asset_importance": 95, "vulnerability_severity": 72, "exploitability": 92, "business_impact": 90, "exposure": 85},
        recommendation_id=None,
        summary="Test summary",
        computed_at=1234567890,
    ))

    # Override dependency
    def override():
        return mock_use_case

    app = create_app()
    app.dependency_overrides[get_evaluate_finding_use_case] = override

    client = TestClient(app)

    payload = {
        "tenant_id": str(uuid4()),
        "asset_id": str(uuid4()),
        "source": "internal_scanner",
        "source_finding_id": "scan-123",
        "title": "Test Finding",
        "description": "Description",
        "raw_severity": 8.5,
        "raw_severity_scale": "cvss_v3",
        "detected_at": 1234567890,
        "raw_payload": {"key": "value"},
        "cve_id": "CVE-2024-12345",
        "status": "open"
    }

    response = client.post("/api/v1/risk/calculate", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "bis" in data
    assert "tier" in data
    assert data["tier"] == "Critical"


def test_get_decision_endpoint_not_found(client):
    """Test get decision endpoint when not found."""
    response = client.get(f"/api/v1/risk/{uuid4()}?tenant_id={uuid4()}")
    assert response.status_code == 404