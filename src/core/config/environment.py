"""Environment detection and management."""

import os
from enum import Enum


class Environment(str, Enum):
    """Runtime environment enumeration."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, value: str) -> "Environment":
        """Parse environment from string.

        Args:
            value: Environment string value.

        Returns:
            Environment: Parsed environment enum.

        Raises:
            ValueError: If environment is invalid.
        """
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ValueError(f"Invalid environment: {value}") from exc

    @property
    def is_development(self) -> bool:
        """Check if environment is development."""
        return self == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if environment is staging."""
        return self == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self == Environment.PRODUCTION

    @property
    def is_production_like(self) -> bool:
        """Check if environment is production or staging."""
        return self in (Environment.PRODUCTION, Environment.STAGING)


def get_environment() -> Environment:
    """Get current environment from environment variables.

    Returns:
        Environment: Current environment enum.
    """
    env = os.getenv("ENV_STATE", "development")
    return Environment.from_string(env)


def is_development() -> bool:
    """Check if current environment is development."""
    return get_environment().is_development


def is_production() -> bool:
    """Check if current environment is production."""
    return get_environment().is_production