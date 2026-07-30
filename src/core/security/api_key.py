"""API key handling for service-to-service authentication."""

import hashlib
import secrets
import time
from typing import Optional, Tuple
from uuid import UUID, uuid4


class APIKeyHandler:
    """API key generator and validator.

    This class handles the generation, hashing, and validation of API keys
    for service-to-service authentication.
    """

    def __init__(self, pepper: str = "") -> None:
        """Initialize API key handler.

        Args:
            pepper: Optional pepper string for additional security.
        """
        self.pepper = pepper

    def generate(self, prefix: str = "qk") -> Tuple[str, str]:
        """Generate a new API key pair.

        Returns a tuple of (raw_key, hashed_key). The raw key should be
        stored securely by the client; the hashed key is stored in the database.

        Args:
            prefix: Prefix for the raw key (default: "qk").

        Returns:
            Tuple[str, str]: (raw_key, hashed_key)
        """
        # Generate a random token
        token = secrets.token_urlsafe(32)

        # Add prefix for identification
        raw_key = f"{prefix}_{token}"

        # Hash the key for storage
        hashed_key = self._hash_key(raw_key)

        return raw_key, hashed_key

    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for storage.

        Args:
            raw_key: Raw API key string.

        Returns:
            str: Hashed key.
        """
        # Combine with pepper
        combined = f"{raw_key}{self.pepper}"

        # Use SHA-256 for hashing
        return hashlib.sha256(combined.encode()).hexdigest()

    def verify(self, raw_key: str, hashed_key: str) -> bool:
        """Verify a raw API key against its hashed version.

        Args:
            raw_key: Raw API key provided by client.
            hashed_key: Hashed key stored in database.

        Returns:
            bool: True if the key matches.
        """
        computed_hash = self._hash_key(raw_key)
        return secrets.compare_digest(computed_hash, hashed_key)

    def generate_tenant_api_key(
        self,
        tenant_id: UUID,
        expires_at: Optional[int] = None,
    ) -> Tuple[str, str]:
        """Generate a tenant-specific API key.

        Args:
            tenant_id: Tenant identifier.
            expires_at: Optional expiration timestamp.

        Returns:
            Tuple[str, str]: (raw_key, hashed_key)
        """
        prefix = f"qk_{str(tenant_id)[:8]}"
        raw_key, hashed_key = self.generate(prefix=prefix)

        # If expiry is provided, we could encode it in the hash
        # For now, we just return the key pair
        return raw_key, hashed_key

    def mask_key(self, raw_key: str) -> str:
        """Mask an API key for display (e.g., in logs).

        Args:
            raw_key: Raw API key.

        Returns:
            str: Masked key showing only prefix and last 4 chars.
        """
        if not raw_key:
            return "***"
        if len(raw_key) <= 8:
            return "***"

        prefix = raw_key[:4]
        suffix = raw_key[-4:]
        return f"{prefix}...{suffix}"