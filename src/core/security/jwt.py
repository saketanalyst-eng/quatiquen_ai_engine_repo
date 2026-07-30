"""JWT token handling for authentication."""

import time
from typing import Any, Dict, Optional, Union
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.core.exceptions.application import ConfigurationError
from src.core.exceptions.domain import ValidationError


class JWTHandler:
    """JWT token encoder and decoder.

    This class handles the generation, validation, and decoding of JWT
    tokens for authentication and authorization.
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        expiry_minutes: int = 10080,
    ) -> None:
        """Initialize JWT handler.

        Args:
            secret: Secret key for signing.
            algorithm: JWT algorithm (HS256 by default).
            expiry_minutes: Token expiry in minutes.
        """
        self.secret = secret
        self.algorithm = algorithm
        self.expiry_minutes = expiry_minutes

    def encode(
        self,
        tenant_id: Union[str, UUID],
        user_id: Union[str, UUID],
        email: str,
        role: str = "member",
        additional_claims: Optional[Dict[str, Any]] = None,
        expiry_minutes: Optional[int] = None,
    ) -> str:
        """Encode a JWT token.

        Args:
            tenant_id: Tenant identifier.
            user_id: User identifier.
            email: User email.
            role: User role (admin/member).
            additional_claims: Extra claims to include.
            expiry_minutes: Override default expiry.

        Returns:
            str: Encoded JWT token.

        Raises:
            ConfigurationError: If secret is not configured.
        """
        if not self.secret:
            raise ConfigurationError("JWT secret is not configured")

        exp_minutes = expiry_minutes or self.expiry_minutes
        now = int(time.time())

        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "tenant": str(tenant_id),
            "email": email,
            "role": role,
            "iat": now,
            "exp": now + (exp_minutes * 60),
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode(self, token: str, verify: bool = True) -> Dict[str, Any]:
        """Decode and validate a JWT token.

        Args:
            token: JWT token string.
            verify: Whether to verify the token signature.

        Returns:
            Dict[str, Any]: Decoded token payload.

        Raises:
            ValidationError: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_signature": verify},
            )
            return payload
        except jwt.ExpiredSignatureError as exc:
            raise ValidationError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise ValidationError(f"Invalid token: {str(exc)}") from exc

    def verify_token(self, token: str) -> bool:
        """Verify a JWT token without returning payload.

        Args:
            token: JWT token string.

        Returns:
            bool: True if token is valid, False otherwise.
        """
        try:
            self.decode(token, verify=True)
            return True
        except ValidationError:
            return False

    def extract_tenant_id(self, token: str) -> Optional[str]:
        """Extract tenant ID from a JWT token.

        Args:
            token: JWT token string.

        Returns:
            Optional[str]: Tenant ID if present, None otherwise.
        """
        try:
            payload = self.decode(token, verify=False)
            return payload.get("tenant")
        except ValidationError:
            return None

    def extract_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from a JWT token.

        Args:
            token: JWT token string.

        Returns:
            Optional[str]: User ID if present, None otherwise.
        """
        try:
            payload = self.decode(token, verify=False)
            return payload.get("sub")
        except ValidationError:
            return None

    def refresh_token(self, token: str, expiry_minutes: Optional[int] = None) -> str:
        """Refresh an existing token.

        Args:
            token: Existing JWT token.
            expiry_minutes: New expiry time.

        Returns:
            str: New JWT token.

        Raises:
            ValidationError: If token is invalid.
        """
        payload = self.decode(token, verify=True)

        # Remove existing exp and iat
        payload.pop("exp", None)
        payload.pop("iat", None)

        # Re-encode with new expiry
        exp_minutes = expiry_minutes or self.expiry_minutes
        now = int(time.time())
        payload["iat"] = now
        payload["exp"] = now + (exp_minutes * 60)

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)