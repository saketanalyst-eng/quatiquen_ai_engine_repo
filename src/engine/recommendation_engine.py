"""Recommendation engine selects remediation guidance from knowledge base."""

import json
import pathlib
from typing import Any, Dict, Optional
from uuid import uuid4

from src.core.logging.logger import get_logger
from src.domain.entities import Recommendation
from src.engine.config import EngineConfig
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.recommendation_engine")


class RecommendationEngine:
    """Selects recommendation from knowledge base based on finding."""

    def __init__(self, config: EngineConfig) -> None:
        """Initialize recommendation engine.

        Args:
            config: Engine configuration.
        """
        self.config = config
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load recommendation templates from JSON file.

        Returns:
            Dict[str, Any]: Knowledge base dictionary.
        """
        kb_path = pathlib.Path("src/knowledge_base/remediation_templates.json")
        try:
            with open(kb_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning("Could not load knowledge base", error=str(exc))
            return {"templates": []}

    async def execute(self, result: EngineResult) -> None:
        """Generate recommendation.

        Args:
            result: Engine result state.

        Returns:
            None: Recommendation is added to result.
        """
        if not self.config.enable_recommendation:
            return

        finding = result.finding
        risk_score = result.risk_score
        drivers = result.drivers
        tier = result.tier

        if any(v is None for v in [finding, risk_score, drivers, tier]):
            logger.warning("Cannot generate recommendation: missing data")
            return

        try:
            # Determine category
            category = self._infer_category(finding)

            # Find best match in knowledge base
            template = self._find_template(category, finding.cve_id)
            if template is None:
                logger.debug("No recommendation template found", category=category)
                if self.config.skip_recommendation_if_no_match:
                    return
                # Fallback: generic
                template = {
                    "technical_text": "Review the finding and apply appropriate remediation.",
                    "estimated_effort": "medium",
                    "estimated_impact": 50,
                }

            # Calculate risk reduction potential
            risk_reduction = self._calculate_risk_reduction(drivers)

            # Create recommendation entity (will be persisted later)
            recommendation = Recommendation.create(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                technical_text=template.get("technical_text", ""),
                estimated_effort=template.get("estimated_effort", "medium"),
                estimated_impact=template.get("estimated_impact", 50),
                risk_reduction_potential=risk_reduction,
                priority=tier,
                category=category,
                business_explanation=None,  # Will be filled by AI later
            )

            # Store recommendation ID in result
            result.recommendation_id = recommendation.id

            logger.debug(
                "Recommendation generated",
                finding_id=str(finding.id),
                category=category,
                effort=recommendation.estimated_effort,
            )

        except Exception as exc:
            logger.error(
                "Recommendation engine failed",
                finding_id=str(finding.id),
                error=str(exc),
                exc_info=True,
            )
            # Non-fatal: continue without recommendation

    def _infer_category(self, finding) -> str:
        """Infer category from finding title/description."""
        if finding.has_cve:
            return "vulnerability"
        title_lower = finding.title.lower()
        if "misconfiguration" in title_lower:
            return "misconfiguration"
        if "missing security headers" in title_lower:
            return "headers"
        if "outdated" in title_lower:
            return "outdated"
        return "general"

    def _find_template(self, category: str, cve_id: str = None) -> Optional[Dict[str, Any]]:
        """Find best matching template from knowledge base."""
        templates = self.knowledge_base.get("templates", [])
        for template in templates:
            if template.get("category") == category:
                return template
        return None

    def _calculate_risk_reduction(self, drivers) -> float:
        """Calculate risk reduction potential (simplified)."""
        # Assume fixing the vulnerability reduces exploitability and vulnerability severity
        # This is a placeholder; in real implementation, recompute score with EX and VS neutralized
        # For now, return a percentage based on exploitability
        exploitability = drivers.exploitability
        if exploitability > 80:
            return 70.0
        if exploitability > 50:
            return 40.0
        return 20.0