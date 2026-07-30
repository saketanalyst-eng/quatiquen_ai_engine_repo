"""OpenTelemetry tracing setup."""

import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Tracer

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.tracing")


class Tracer:
    """OpenTelemetry tracer wrapper."""

    def __init__(
        self,
        service_name: str = "quantiquan-ai-engine",
        service_version: str = "1.0.0",
        enabled: bool = True,
        otlp_endpoint: Optional[str] = None,
    ) -> None:
        """Initialize tracer.

        Args:
            service_name: Service name.
            service_version: Service version.
            enabled: Whether tracing is enabled.
            otlp_endpoint: OTLP collector endpoint.
        """
        self.service_name = service_name
        self.service_version = service_version
        self.enabled = enabled
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")

        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer: Optional[Tracer] = None

        if enabled:
            self._setup()

    def _setup(self) -> None:
        """Set up OpenTelemetry tracing."""
        try:
            resource = Resource.create(
                {
                    SERVICE_NAME: self.service_name,
                    SERVICE_VERSION: self.service_version,
                }
            )

            provider = TracerProvider(resource=resource)

            if self.otlp_endpoint:
                exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint, insecure=True)
                processor = BatchSpanProcessor(exporter)
                provider.add_span_processor(processor)

            trace.set_tracer_provider(provider)
            self._tracer_provider = provider
            self._tracer = trace.get_tracer(self.service_name, self.service_version)

            logger.info("Tracing initialized", endpoint=self.otlp_endpoint)

        except Exception as exc:
            logger.warning("Failed to initialize tracing", error=str(exc))
            self.enabled = False

    def get_tracer(self) -> Optional[Tracer]:
        """Get the tracer instance.

        Returns:
            Optional[Tracer]: Tracer instance or None.
        """
        return self._tracer

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Optional[Span]]:
        """Start a new span with context manager.

        Args:
            name: Span name.
            attributes: Span attributes.

        Yields:
            Optional[Span]: Span object or None.
        """
        if not self.enabled or not self._tracer:
            yield None
            return

        with self._tracer.start_as_current_span(name, attributes=attributes) as span:
            yield span

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an event to the current span.

        Args:
            name: Event name.
            attributes: Event attributes.
        """
        if not self.enabled:
            return

        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(name, attributes=attributes)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the current span.

        Args:
            key: Attribute key.
            value: Attribute value.
        """
        if not self.enabled:
            return

        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(key, str(value))

    def set_status(self, status: str, description: str = "") -> None:
        """Set status on the current span.

        Args:
            status: Status (OK, ERROR).
            description: Status description.
        """
        if not self.enabled:
            return

        current_span = trace.get_current_span()
        if current_span:
            if status.upper() == "OK":
                current_span.set_status(trace.StatusCode.OK)
            else:
                current_span.set_status(trace.StatusCode.ERROR, description)

    def shutdown(self) -> None:
        """Shutdown tracer provider."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Optional[Tracer]:
    """Get the global tracer instance.

    Returns:
        Optional[Tracer]: Global tracer instance.
    """
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer