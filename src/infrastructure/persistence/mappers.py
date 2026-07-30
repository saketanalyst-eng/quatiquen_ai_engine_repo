"""Mappers between domain entities and ORM models."""

from typing import List, Optional
from uuid import UUID

from src.core.constants.enums import ComplianceScope, DataSensitivity, ExposureLevel, FindingSource, FindingStatus
from src.domain.entities import Asset, Decision, Finding, Recommendation
from src.domain.value_objects import BusinessContext, Confidence, Drivers, RiskScore
from src.infrastructure.persistence.models import (
    AssetModel,
    DecisionModel,
    FindingModel,
    RecommendationModel,
    ScoreDriversModel,
)


class FindingMapper:
    """Mapper for Finding entity."""

    @staticmethod
    def to_domain(model: FindingModel) -> Finding:
        """Convert ORM model to domain entity."""
        return Finding(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            asset_id=UUID(model.asset_id),
            source=FindingSource(model.source),
            source_finding_id=model.source_finding_id,
            cve_id=model.cve_id,
            title=model.title,
            description=model.description,
            raw_severity=model.raw_severity,
            raw_severity_scale=model.raw_severity_scale,
            status=FindingStatus(model.status),
            detected_at=model.detected_at,
            raw_payload=model.raw_payload,
            created_at=int(model.created_at.timestamp()),
            updated_at=int(model.updated_at.timestamp()),
        )

    @staticmethod
    def to_model(entity: Finding) -> FindingModel:
        """Convert domain entity to ORM model."""
        return FindingModel(
            id=str(entity.id),  # ✅ Convert UUID to string
            tenant_id=str(entity.tenant_id),  # ✅ Convert UUID to string
            asset_id=str(entity.asset_id),  # ✅ Convert UUID to string
            source=entity.source.value,
            source_finding_id=entity.source_finding_id,
            cve_id=entity.cve_id,
            title=entity.title,
            description=entity.description,
            raw_severity=entity.raw_severity,
            raw_severity_scale=entity.raw_severity_scale,
            status=entity.status.value,
            detected_at=entity.detected_at,
            raw_payload=entity.raw_payload,
        )


class AssetMapper:
    """Mapper for Asset entity and BusinessContext."""

    @staticmethod
    def to_domain(model: AssetModel) -> Asset:
        """Convert ORM model to domain entity."""
        return Asset(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            name=model.name,
            asset_type=model.asset_type,
            importance_tier=model.importance_tier,
            owner_id=UUID(model.owner_id) if model.owner_id else None,
            data_classification=DataSensitivity(model.data_classification),
            compliance_scopes=[ComplianceScope(s) for s in model.compliance_scopes],
            exposure=ExposureLevel(model.exposure),
            is_production=model.is_production,
            downstream_dependents=model.downstream_dependents,
            revenue_impact=model.revenue_impact,
            created_at=int(model.created_at.timestamp()),
            updated_at=int(model.updated_at.timestamp()),
        )

    @staticmethod
    def to_business_context(model: AssetModel) -> BusinessContext:
        """Convert ORM model to BusinessContext value object."""
        return BusinessContext(
            asset_id=UUID(model.id),
            importance_tier=model.importance_tier,
            owner_id=UUID(model.owner_id) if model.owner_id else None,
            data_classification=DataSensitivity(model.data_classification),
            compliance_scopes=[ComplianceScope(s.lower()) for s in model.compliance_scopes],
            exposure=ExposureLevel(model.exposure),
            is_production=model.is_production,
            downstream_dependents=model.downstream_dependents,
            revenue_impact=model.revenue_impact,
        )


class DecisionMapper:
    """Mapper for Decision aggregate and related models."""

    @staticmethod
    def to_domain(
        decision_model: DecisionModel,
        driver_models: List[ScoreDriversModel],
        rec_model: Optional[RecommendationModel],
    ) -> Decision:
        """Convert ORM models to Decision entity."""
        # Build drivers
        drivers_dict = {}
        for dm in driver_models:
            drivers_dict[dm.factor] = dm.value
        drivers = Drivers(
            asset_importance=drivers_dict.get("asset_importance", 0),
            vulnerability_severity=drivers_dict.get("vulnerability_severity", 0),
            exploitability=drivers_dict.get("exploitability", 0),
            business_impact=drivers_dict.get("business_impact", 0),
            exposure=drivers_dict.get("exposure", 0),
        )

        risk_score = RiskScore(
            raw_bis=drivers.raw_bis,
            final_bis=decision_model.bis,
            confidence_multiplier=0.7 + 0.3 * decision_model.confidence,
        )

        confidence = Confidence(value=decision_model.confidence, deductions=())

        return Decision(
            finding_id=UUID(decision_model.finding_id),
            tenant_id=UUID(decision_model.tenant_id),
            risk_score=risk_score,
            tier=decision_model.tier,
            confidence=confidence,
            drivers=drivers,
            recommendation_id=UUID(rec_model.id) if rec_model else None,
            summary=rec_model.business_explanation if rec_model else None,
            computed_at=decision_model.computed_at,
            version=decision_model.version,
        )

    @staticmethod
    def to_model(decision: Decision) -> tuple[DecisionModel, List[ScoreDriversModel], Optional[RecommendationModel]]:
        """Convert Decision to ORM models."""
        decision_model = DecisionModel(
            id=None,  # Let DB generate
            finding_id=str(decision.finding_id),  # ✅ Convert UUID to string
            tenant_id=str(decision.tenant_id),  # ✅ Convert UUID to string
            bis=decision.bis,
            tier=decision.tier.value,
            confidence=decision.confidence.value,
            computed_at=decision.computed_at,
            version=decision.version,
        )

        # Drivers
        driver_models = []
        for factor, value in decision.drivers.to_dict().items():
            weight = {
                "asset_importance": 0.25,
                "vulnerability_severity": 0.20,
                "exploitability": 0.25,
                "business_impact": 0.20,
                "exposure": 0.10,
            }.get(factor, 0.0)
            driver_models.append(
                ScoreDriversModel(
                    risk_score_id=decision_model.id,
                    factor=factor,
                    value=value,
                    weight=weight,
                )
            )

        # Recommendation
        rec_model = None
        if decision.recommendation_id:
            rec_model = RecommendationModel(
                id=str(decision.recommendation_id),  # ✅ Convert UUID to string
                finding_id=str(decision.finding_id),  # ✅ Convert UUID to string
                tenant_id=str(decision.tenant_id),  # ✅ Convert UUID to string
                technical_text="",
                business_explanation=decision.summary,
                estimated_effort="medium",
                estimated_impact=50,
                risk_reduction_potential=0,
                priority=decision.tier.value,
                category="general",
            )

        return decision_model, driver_models, rec_model