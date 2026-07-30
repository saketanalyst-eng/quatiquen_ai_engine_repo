"""Prompt templates for LLM interactions."""

from src.ai.prompts.summary_prompt import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT_TEMPLATE
from src.ai.prompts.recommendation_prompt import RECOMMENDATION_SYSTEM_PROMPT, RECOMMENDATION_USER_PROMPT_TEMPLATE
from src.ai.prompts.explanation_prompt import EXPLANATION_SYSTEM_PROMPT, EXPLANATION_USER_PROMPT_TEMPLATE
from src.ai.prompts.prompt_builder import PromptBuilder

__all__ = [
    "SUMMARY_SYSTEM_PROMPT",
    "SUMMARY_USER_PROMPT_TEMPLATE",
    "RECOMMENDATION_SYSTEM_PROMPT",
    "RECOMMENDATION_USER_PROMPT_TEMPLATE",
    "EXPLANATION_SYSTEM_PROMPT",
    "EXPLANATION_USER_PROMPT_TEMPLATE",
    "PromptBuilder",
]