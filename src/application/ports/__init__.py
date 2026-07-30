"""Ports (interfaces) for external dependencies."""

from src.application.ports.cache_port import CachePort
from src.application.ports.event_port import EventPort
from src.application.ports.llm_port import LLMPort
from src.application.ports.threat_intel_port import ThreatIntelPort

__all__ = [
    "CachePort",
    "EventPort",
    "LLMPort",
    "ThreatIntelPort",
]