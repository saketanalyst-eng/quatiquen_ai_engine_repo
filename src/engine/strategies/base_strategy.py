"""Base strategy for scoring overrides."""

from abc import ABC, abstractmethod
from typing import Tuple


class Strategy(ABC):
    """Abstract strategy for modifying scoring inputs."""

    @abstractmethod
    def modify_scores(
        self,
        asset_importance: float,
        vulnerability_severity: float,
        exploitability: float,
        business_impact: float,
        exposure: float,
    ) -> Tuple[float, float, float, float, float]:
        """Modify the five driver scores before BIS calculation.

        Args:
            asset_importance: Original asset importance.
            vulnerability_severity: Original vulnerability severity.
            exploitability: Original exploitability.
            business_impact: Original business impact.
            exposure: Original exposure.

        Returns:
            Tuple[float, ...]: Modified scores (same order).
        """
        pass