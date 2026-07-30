"""Threshold values for priority bands and confidence.

These are defined in Sections 7.4 and 9 of the Risk Engine Blueprint.
"""

from typing import Dict, Tuple

# Priority bands (Section 7.4)
TIER_CRITICAL_LOW: int = 85
TIER_CRITICAL_UPPER: int = 100
TIER_HIGH_LOW: int = 65
TIER_HIGH_UPPER: int = 84
TIER_MEDIUM_LOW: int = 35
TIER_MEDIUM_UPPER: int = 64
TIER_LOW_LOW: int = 0
TIER_LOW_UPPER: int = 34

# Confidence thresholds (Section 9)
CONFIDENCE_FLOOR: float = 0.7
CONFIDENCE_LOW_THRESHOLD: float = 0.7
CONFIDENCE_MAX: float = 1.0
CONFIDENCE_MIN: float = 0.0
CONFIDENCE_MULTIPLIER_BASE: float = 0.7   # <-- added
CONFIDENCE_MULTIPLIER_SCALE: float = 0.3  # <-- added

# Confidence deductions (Section 9)
DEDUCTION_NO_OWNER: float = 0.2
DEDUCTION_STALE_SCAN_DAYS: int = 30
DEDUCTION_STALE_SCAN: float = 0.2
DEDUCTION_NO_THREAT_INTEL: float = 0.1
DEDUCTION_NO_CMDB: float = 0.3
DEDUCTION_SINGLE_SOURCE: float = 0.1

# Priority bands as a dict for easy lookup
PRIORITY_BANDS: Dict[str, Tuple[int, int]] = {
    "Critical": (TIER_CRITICAL_LOW, TIER_CRITICAL_UPPER),
    "High": (TIER_HIGH_LOW, TIER_HIGH_UPPER),
    "Medium": (TIER_MEDIUM_LOW, TIER_MEDIUM_UPPER),
    "Low": (TIER_LOW_LOW, TIER_LOW_UPPER),
}

# Compliance floor raises (Section 5)
COMPLIANCE_FLOOR_RAISE: Dict[str, int] = {
    "none": 0,
    "pci": 25,
    "dpdp": 20,
    "iso27001": 15,
    "soc2": 20,
}

# Data sensitivity multipliers (Section 5)
DATA_SENSITIVITY_MULTIPLIER: Dict[str, float] = {
    "public": 1.0,
    "internal": 1.2,
    "confidential": 1.5,
    "regulated": 2.0,
}