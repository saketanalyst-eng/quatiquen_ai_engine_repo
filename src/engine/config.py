"""Engine-specific configuration."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EngineConfig:
    """Configuration for the scoring pipeline."""

    # Timeouts in seconds
    context_fetch_timeout: float = 2.0
    threat_intel_timeout: float = 1.5
    llm_timeout: float = 2.0
    total_pipeline_timeout: float = 5.0

    # Retry settings
    context_retries: int = 2
    threat_intel_retries: int = 2
    llm_retries: int = 1

    # Feature flags
    enable_ai_summary: bool = True
    enable_recommendation: bool = True
    enable_compliance_rules: bool = True
    enable_confidence: bool = True

    # Conditional execution
    skip_summary_on_low_confidence: bool = True
    skip_summary_if_no_cve: bool = True
    skip_recommendation_if_no_match: bool = True

    # Confidence threshold for skipping summary
    low_confidence_threshold: float = 0.7

    # Max findings per batch
    batch_size: int = 100

    # Default values for missing data
    default_vulnerability_severity: float = 50.0
    default_asset_importance: float = 50.0

    # Strategy selection
    strategy_name: str = "default"


DEFAULT_CONFIG = EngineConfig()