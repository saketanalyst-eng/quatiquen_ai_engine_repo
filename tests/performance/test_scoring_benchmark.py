"""Performance benchmarks for scoring engine."""

import pytest
from src.domain.services import ScoringEngine
from src.domain.value_objects import BusinessContext, ThreatContext


@pytest.mark.benchmark
def test_scoring_engine_benchmark(benchmark):
    """Benchmark the full scoring pipeline."""
    business_context = BusinessContext(
        asset_id=MagicMock(),
        importance_tier=90,
        owner_id=MagicMock(),
        data_classification="regulated",
        compliance_scopes=["PCI"],
        exposure="customer-facing",
        is_production=True,
        downstream_dependents=15,
        revenue_impact="high",
    )
    threat_context = ThreatContext.create(
        cve_id="CVE-2024-12345",
        epss_score=0.85,
        is_kev=True,
        has_poc=True,
    )

    def score():
        return ScoringEngine.score_finding(
            business_context=business_context,
            threat_context=threat_context,
            vulnerability_severity=72.0,
            is_stale=False,
            source_count=3,
            has_cmdb_record=True,
        )

    result = benchmark(score)
    assert result[0].final_bis > 0
