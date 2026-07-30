"""Scoring weights for Business Impact Score (BIS) calculation.

These weights are defined in Section 7.2 of the Risk Engine Blueprint.
"""

# Asset Importance weight - 25%
ASSET_IMPORTANCE_WEIGHT: float = 0.25

# Vulnerability Severity weight - 20%
VULNERABILITY_SEVERITY_WEIGHT: float = 0.20

# Exploitability weight - 25%
EXPLOITABILITY_WEIGHT: float = 0.25

# Business Impact weight - 20%
BUSINESS_IMPACT_WEIGHT: float = 0.20

# Exposure weight - 10%
EXPOSURE_WEIGHT: float = 0.10

# Sum of all weights (should equal 1.0)
TOTAL_WEIGHT_SUM: float = (
    ASSET_IMPORTANCE_WEIGHT
    + VULNERABILITY_SEVERITY_WEIGHT
    + EXPLOITABILITY_WEIGHT
    + BUSINESS_IMPACT_WEIGHT
    + EXPOSURE_WEIGHT
)

# Confidence floor from Section 9
CONFIDENCE_FLOOR: float = 0.7
CONFIDENCE_MULTIPLIER_BASE: float = 0.7
CONFIDENCE_MULTIPLIER_SCALE: float = 0.3