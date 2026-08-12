"""Priority mapping for decision objects."""

from src.core.constants.enums import PriorityTier


class PriorityMapping:
    """Maps risk tiers to business decisions, priority levels, and due times."""

    TIER_MAP = {
        PriorityTier.CRITICAL: {
            "decision": "Immediate Action Required",
            "priority": "P0",
            "due_hours": 4,
            "color": "red",
        },
        PriorityTier.HIGH: {
            "decision": "Urgent Patch Required",
            "priority": "P1",
            "due_hours": 24,
            "color": "orange",
        },
        PriorityTier.MEDIUM: {
            "decision": "Plan for Next Sprint",
            "priority": "P2",
            "due_hours": 168,  # 7 days
            "color": "yellow",
        },
        PriorityTier.LOW: {
            "decision": "Monitor and Track",
            "priority": "P3",
            "due_hours": 720,  # 30 days
            "color": "green",
        },
    }

    @classmethod
    def get(cls, tier: PriorityTier) -> dict:
        """Get mapping for a given tier."""
        return cls.TIER_MAP.get(tier, cls.TIER_MAP[PriorityTier.MEDIUM])

    @classmethod
    def get_decision(cls, tier: PriorityTier) -> str:
        """Get decision text for a tier."""
        return cls.get(tier)["decision"]

    @classmethod
    def get_priority(cls, tier: PriorityTier) -> str:
        """Get priority level (P0, P1, P2, P3)."""
        return cls.get(tier)["priority"]

    @classmethod
    def get_due_hours(cls, tier: PriorityTier) -> int:
        """Get due time in hours."""
        return cls.get(tier)["due_hours"]

    @classmethod
    def get_due_text(cls, tier: PriorityTier) -> str:
        """Get human‑readable due time."""
        hours = cls.get_due_hours(tier)
        if hours <= 4:
            return f"Within {hours} hours"
        elif hours <= 24:
            return f"Within {hours} hours"
        else:
            days = hours // 24
            return f"Within {days} days"