"""Builds prompts from templates and context."""

from typing import Any, Dict

from src.ai.prompts import (
    EXPLANATION_SYSTEM_PROMPT,
    EXPLANATION_USER_PROMPT_TEMPLATE,
    RECOMMENDATION_SYSTEM_PROMPT,
    RECOMMENDATION_USER_PROMPT_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT_TEMPLATE,
)


class PromptBuilder:
    """Builds prompts for various LLM tasks."""

    @staticmethod
    def build_summary_prompt(context: Dict[str, Any]) -> tuple[str, str]:
        """Build system and user prompts for summary generation.

        Args:
            context: Dictionary with fields: title, description, cve_id, asset_name,
                     asset_importance, exposure, business_impact, exploitability,
                     vulnerability_severity, confidence, tier.

        Returns:
            tuple[str, str]: (system_prompt, user_prompt)
        """
        user_prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(
            title=context.get("title", "Unknown finding"),
            description=context.get("description", "No description provided."),
            cve_id=context.get("cve_id", "None"),
            asset_name=context.get("asset_name", "Unknown"),
            asset_importance=context.get("asset_importance", 50),
            exposure=context.get("exposure", "Internal"),
            business_impact=context.get("business_impact", 50),
            exploitability=context.get("exploitability", 50),
            vulnerability_severity=context.get("vulnerability_severity", 50),
            confidence=context.get("confidence", 0.8),
            tier=context.get("tier", "Medium"),
        )
        return SUMMARY_SYSTEM_PROMPT, user_prompt

    @staticmethod
    def build_recommendation_prompt(context: Dict[str, Any]) -> tuple[str, str]:
        """Build system and user prompts for recommendation explanation.

        Args:
            context: Dictionary with fields: title, description, cve_id, asset_name,
                     tier, business_impact, exploitability, technical_text,
                     estimated_effort, risk_reduction_potential.

        Returns:
            tuple[str, str]: (system_prompt, user_prompt)
        """
        user_prompt = RECOMMENDATION_USER_PROMPT_TEMPLATE.format(
            title=context.get("title", "Unknown finding"),
            description=context.get("description", "No description provided."),
            cve_id=context.get("cve_id", "None"),
            asset_name=context.get("asset_name", "Unknown"),
            tier=context.get("tier", "Medium"),
            business_impact=context.get("business_impact", 50),
            exploitability=context.get("exploitability", 50),
            technical_text=context.get("technical_text", "Review and remediate."),
            estimated_effort=context.get("estimated_effort", "medium"),
            risk_reduction_potential=context.get("risk_reduction_potential", 20),
        )
        return RECOMMENDATION_SYSTEM_PROMPT, user_prompt

    @staticmethod
    def build_explanation_prompt(context: Dict[str, Any]) -> tuple[str, str]:
        """Build system and user prompts for generic explanation.

        Args:
            context: Dictionary with fields: title, description, context.

        Returns:
            tuple[str, str]: (system_prompt, user_prompt)
        """
        user_prompt = EXPLANATION_USER_PROMPT_TEMPLATE.format(
            title=context.get("title", "Security finding"),
            description=context.get("description", "No description provided."),
            context=context.get("context", "General security risk."),
        )
        return EXPLANATION_SYSTEM_PROMPT, user_prompt