"""Application settings management using Pydantic BaseSettings."""

import json
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, SecretStr, field_validator, AnyUrl
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = Field("quantiquan-ai-engine", description="Application name")
    app_version: str = Field("1.0.0", description="Application version")
    environment: str = Field("development", description="Runtime environment")
    debug: bool = Field(False, description="Enable debug mode")
    log_level: str = Field("INFO", description="Logging level")

    api_prefix: str = Field("/api/v1", description="Base API path")
    allowed_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # Database URL – now accepts PostgreSQL, SQLite, or any valid DB URL
    database_url: str = Field(
        "sqlite+aiosqlite:///./quantiquan.db",
        description="Database connection string (PostgreSQL or SQLite)",
    )
    database_pool_size: int = Field(10, description="Connection pool size")
    database_max_overflow: int = Field(20, description="Max overflow connections")

    redis_url: str = Field(
        "redis://localhost:6379/0",
        description="Redis connection string",
    )
    redis_ttl_default: int = Field(300, description="Default cache TTL (seconds)")
    redis_threat_ttl: int = Field(86400, description="Threat intel cache TTL (24h)")

    groq_api_key: SecretStr = Field(..., description="Groq API secret key")
    groq_model: str = Field("mixtral-8x7b-32768", description="Groq model")
    groq_timeout_seconds: float = Field(2.0, description="Groq request timeout")
    groq_max_retries: int = Field(2, description="Maximum retries for Groq")

    jwt_secret: SecretStr = Field(..., description="JWT signing secret")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    jwt_expiry_minutes: int = Field(60 * 24 * 7, description="JWT expiration (7 days)")

    api_key_header: str = Field("X-API-Key", description="API key header name")

    rate_limit_per_minute: int = Field(100, description="Single finding rate limit")
    bulk_rate_limit_per_minute: int = Field(10, description="Bulk rate limit")

    epss_api_url: str = Field(
        "https://api.first.org/epss/v1/",
        description="EPSS API endpoint",
    )
    epss_cache_ttl: int = Field(86400, description="EPSS cache TTL (24h)")

    kev_feed_url: str = Field(
        "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        description="CISA KEV feed URL",
    )
    kev_cache_ttl: int = Field(86400, description="KEV cache TTL (24h)")

    enable_telemetry: bool = Field(False, description="Enable OpenTelemetry")
    prometheus_port: int = Field(9090, description="Prometheus metrics port")

    audit_log_enabled: bool = Field(True, description="Enable audit logging")

    circuit_breaker_failure_threshold: int = Field(
        5,
        description="Circuit breaker failure threshold",
    )
    circuit_breaker_timeout_seconds: int = Field(
        30,
        description="Circuit breaker timeout",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        """Parse allowed origins from string or list."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [x.strip() for x in value.split(",") if x.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure database URL is provided and not empty."""
        if not value:
            raise ValueError("DATABASE_URL must be set")
        return value

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Validate environment value."""
        valid = {"development", "staging", "production"}
        if value not in valid:
            raise ValueError(f"environment must be one of {valid}")
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Get cached application settings.

    Returns:
        AppSettings: Application configuration instance.
    """
    return AppSettings()


Settings = AppSettings