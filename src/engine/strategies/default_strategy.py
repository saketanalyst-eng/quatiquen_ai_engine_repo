"""Default strategy that applies no modifications."""

from typing import Tuple

from src.engine.strategies.base_strategy import Strategy


class DefaultStrategy(Strategy):
    """Default strategy - no modifications."""

    def modify_scores(
        self,
        asset_importance: float,
        vulnerability_severity: float,
        exploitability: float,
        business_impact: float,
        exposure: float,
    ) -> Tuple[float, float, float, float, float]:
        """Return scores unchanged."""
        return (asset_importance, vulnerability_severity, exploitability, business_impact, exposure)