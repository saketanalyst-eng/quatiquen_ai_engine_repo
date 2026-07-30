"""Domain enumerations and constants."""

from enum import Enum, IntEnum, auto


class PriorityTier(str, Enum):
    """Risk priority tier bands."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    @classmethod
    def from_value(cls, value: int) -> "PriorityTier":
        """Get priority tier from numeric BIS value.

        Args:
            value: Final BIS score (0-100).

        Returns:
            PriorityTier: Corresponding priority tier.

        Raises:
            ValueError: If value is out of range.
        """
        if 0 <= value < 35:
            return cls.LOW
        if 35 <= value < 65:
            return cls.MEDIUM
        if 65 <= value < 85:
            return cls.HIGH
        if 85 <= value <= 100:
            return cls.CRITICAL
        raise ValueError(f"BIS value {value} out of range (0-100)")


class FindingStatus(str, Enum):
    """Status of a finding."""

    OPEN = "open"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class FindingSource(str, Enum):
    """Source of a finding."""

    INTERNAL_SCANNER = "internal_scanner"
    EXTERNAL_SCANNER = "external_scanner"
    CLOUD_API = "cloud_api"
    THREAT_FEED = "threat_feed"
    CUSTOM = "custom"


class TenantPlan(str, Enum):
    """Tenant subscription plan."""

    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class DataSensitivity(str, Enum):
    """Data sensitivity classification."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"


class ComplianceScope(str, Enum):
    """Compliance framework scope."""

    NONE = "none"
    PCI = "pci"
    DPDP = "dpdp"
    ISO27001 = "iso27001"
    SOC2 = "soc2"


class AssetCriticality(IntEnum):
    """Asset criticality levels (0-100)."""

    LOW = 25
    MEDIUM = 50
    HIGH = 75
    CRITICAL = 95

    @classmethod
    def from_importance_tier(cls, tier: int) -> "AssetCriticality":
        """Get criticality enum from numeric tier.

        Args:
            tier: Importance tier value (0-100).

        Returns:
            AssetCriticality: Closest criticality level.
        """
        if tier >= 85:
            return cls.CRITICAL
        if tier >= 65:
            return cls.HIGH
        if tier >= 35:
            return cls.MEDIUM
        return cls.LOW


class BusinessImpactLevel(str, Enum):
    """Business impact level."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def from_string(cls, value: str) -> "BusinessImpactLevel":
        """Parse impact level from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.NONE


class ExposureLevel(str, Enum):
    """Exposure level."""

    INTERNAL_ONLY = "internal-only"
    CUSTOMER_AUTHENTICATED = "customer-authenticated"
    CUSTOMER_FACING = "customer-facing"
    INTERNET_FACING = "internet-facing"

    @classmethod
    def from_string(cls, value: str) -> "ExposureLevel":
        """Parse exposure level from string."""
        try:
            return cls(value.lower().replace(" ", "-"))
        except ValueError:
            return cls.INTERNAL_ONLY

    def score(self) -> int:
        """Convert exposure level to 0-100 score.

        Returns:
            int: Exposure score.
        """
        mapping = {
            ExposureLevel.INTERNAL_ONLY: 20,
            ExposureLevel.CUSTOMER_AUTHENTICATED: 50,
            ExposureLevel.CUSTOMER_FACING: 70,
            ExposureLevel.INTERNET_FACING: 90,
        }
        return mapping.get(self, 20)