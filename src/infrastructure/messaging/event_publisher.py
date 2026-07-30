"""Event publisher using Redis."""

import json
from typing import Any, Dict, List

import redis.asyncio as redis

from src.application.ports import EventPort
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.infrastructure.event_publisher")


class EventPublisher(EventPort):
    """Redis-based event publisher implementing EventPort."""

    def __init__(self, redis_url: str, channel_prefix: str = "events") -> None:
        """Initialize event publisher.

        Args:
            redis_url: Redis connection URL.
            channel_prefix: Prefix for Redis channels.
        """
        self.redis_url = redis_url
        self.channel_prefix = channel_prefix
        self.client: redis.Redis = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.client is None:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
        return self.client

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish a single event."""
        try:
            client = await self._get_client()
            channel = f"{self.channel_prefix}:{event_type}"
            message = json.dumps(payload, default=str)
            await client.publish(channel, message)
            logger.debug("Event published", channel=channel, payload=payload)
        except Exception as exc:
            logger.error("Failed to publish event", event_type=event_type, error=str(exc), exc_info=True)

    async def publish_batch(self, events: List[tuple[str, Dict[str, Any]]]) -> None:
        """Publish multiple events."""
        try:
            client = await self._get_client()
            pipeline = client.pipeline()
            for event_type, payload in events:
                channel = f"{self.channel_prefix}:{event_type}"
                message = json.dumps(payload, default=str)
                pipeline.publish(channel, message)
            await pipeline.execute()
            logger.debug("Batch events published", count=len(events))
        except Exception as exc:
            logger.error("Failed to publish batch events", error=str(exc), exc_info=True)