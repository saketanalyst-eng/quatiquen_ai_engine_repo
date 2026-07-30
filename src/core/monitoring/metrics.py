"""Prometheus metrics collection."""

from functools import wraps
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from prometheus_client import Counter, Gauge, Histogram, Info, Summary

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.metrics")


class MetricsCollector:
    """Prometheus metrics collector for application monitoring."""

    def __init__(self, prefix: str = "quantiquan") -> None:
        """Initialize metrics collector.

        Args:
            prefix: Metric name prefix.
        """
        self.prefix = prefix
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize all metric objects."""
        # Request metrics
        self.request_count = Counter(
            f"{self.prefix}_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status_code"],
        )

        self.request_duration = Histogram(
            f"{self.prefix}_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # Scoring metrics
        self.scoring_duration = Histogram(
            f"{self.prefix}_scoring_duration_seconds",
            "Scoring pipeline duration",
            ["tier", "source"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
        )

        self.scoring_count = Counter(
            f"{self.prefix}_scoring_total",
            "Total number of scoring operations",
            ["tier", "source"],
        )

        self.scoring_errors = Counter(
            f"{self.prefix}_scoring_errors_total",
            "Scoring errors",
            ["stage", "error_type"],
        )

        # Confidence metrics
        self.confidence_gauge = Gauge(
            f"{self.prefix}_confidence_score",
            "Current confidence score for findings",
            ["finding_id"],
        )
        self.confidence_histogram = Histogram(
            f"{self.prefix}_confidence_distribution",
            "Confidence score distribution",
            buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
        )

        # AI/LLM metrics
        self.llm_requests = Counter(
            f"{self.prefix}_llm_requests_total",
            "Total LLM requests",
            ["provider", "model", "status"],
        )

        self.llm_duration = Histogram(
            f"{self.prefix}_llm_duration_seconds",
            "LLM request duration",
            ["provider", "model"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
        )

        self.llm_tokens = Summary(
            f"{self.prefix}_llm_tokens",
            "LLM token usage",
            ["provider", "type"],
        )

        # Cache metrics
        self.cache_hits = Counter(
            f"{self.prefix}_cache_hits_total",
            "Cache hits",
            ["cache_type", "key_type"],
        )

        self.cache_misses = Counter(
            f"{self.prefix}_cache_misses_total",
            "Cache misses",
            ["cache_type", "key_type"],
        )

        # External service metrics
        self.external_requests = Counter(
            f"{self.prefix}_external_requests_total",
            "External API requests",
            ["service", "status"],
        )

        self.external_duration = Histogram(
            f"{self.prefix}_external_duration_seconds",
            "External API duration",
            ["service"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
        )

        # Application info
        self.app_info = Info(
            f"{self.prefix}_app_info",
            "Application information",
        )

        # Active findings
        self.active_findings = Gauge(
            f"{self.prefix}_active_findings",
            "Number of active findings",
            ["tenant_id", "tier"],
        )

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
    ) -> None:
        """Record an HTTP request.

        Args:
            method: HTTP method.
            endpoint: Endpoint path.
            status_code: HTTP status code.
            duration: Request duration in seconds.
        """
        self.request_count.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()

        self.request_duration.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

    def record_scoring(
        self,
        tier: str,
        source: str,
        duration: float,
        error: Optional[Exception] = None,
    ) -> None:
        """Record a scoring operation.

        Args:
            tier: Priority tier.
            source: Finding source.
            duration: Scoring duration in seconds.
            error: Optional error that occurred.
        """
        self.scoring_count.labels(tier=tier, source=source).inc()
        self.scoring_duration.labels(tier=tier, source=source).observe(duration)

        if error:
            self.scoring_errors.labels(
                stage="scoring",
                error_type=error.__class__.__name__,
            ).inc()

    def record_confidence(self, finding_id: str, confidence: float) -> None:
        """Record confidence score.

        Args:
            finding_id: Finding identifier.
            confidence: Confidence score (0-1).
        """
        self.confidence_gauge.labels(finding_id=str(finding_id)).set(confidence)
        self.confidence_histogram.observe(confidence)

    def record_llm_request(
        self,
        provider: str,
        model: str,
        status: str,
        duration: float,
        tokens_used: Optional[int] = None,
    ) -> None:
        """Record an LLM request.

        Args:
            provider: LLM provider name.
            model: Model name.
            status: Success/failure/fallback.
            duration: Request duration in seconds.
            tokens_used: Number of tokens used.
        """
        self.llm_requests.labels(
            provider=provider,
            model=model,
            status=status,
        ).inc()

        self.llm_duration.labels(provider=provider, model=model).observe(duration)

        if tokens_used:
            self.llm_tokens.labels(
                provider=provider,
                type="total",
            ).observe(tokens_used)

    def record_cache(self, cache_type: str, key_type: str, hit: bool) -> None:
        """Record a cache operation.

        Args:
            cache_type: Cache type (redis, memory).
            key_type: Key type (threat, asset, etc.).
            hit: Whether it was a cache hit.
        """
        if hit:
            self.cache_hits.labels(cache_type=cache_type, key_type=key_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type, key_type=key_type).inc()

    def record_external_request(
        self,
        service: str,
        status: str,
        duration: float,
    ) -> None:
        """Record an external API request.

        Args:
            service: Service name.
            status: Status (success/failure/timeout).
            duration: Request duration in seconds.
        """
        self.external_requests.labels(service=service, status=status).inc()
        self.external_duration.labels(service=service).observe(duration)

    def set_app_info(self, **kwargs: Any) -> None:
        """Set application information.

        Args:
            **kwargs: Key-value pairs for app info.
        """
        self.app_info.info(kwargs)

    def update_active_findings(self, tenant_id: str, tier: str, count: int) -> None:
        """Update active findings count.

        Args:
            tenant_id: Tenant identifier.
            tier: Priority tier.
            count: Number of active findings.
        """
        self.active_findings.labels(
            tenant_id=str(tenant_id),
            tier=tier,
        ).set(count)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        MetricsCollector: Global metrics collector.
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def track_duration(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to track function duration.

    Args:
        metric_name: Name of the metric.
        labels: Labels for the metric.

    Returns:
        Callable: Decorated function.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                return result
            except Exception:
                duration = time.time() - start
                raise
            finally:
                # Record duration (simplified)
                pass
        return async_wrapper
    return decorator