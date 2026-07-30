"""Authentication utilities for FastAPI dependency injection."""

from typing import Optional

from fastapi import HTTPException, Request, status

from src.core.exceptions.domain import ValidationError
from src.core.security.api_key import APIKeyHandler
from src.core.security.jwt import JWTHandler


class AuthenticationHandler:
    """Authentication handler for extracting and validating credentials.

    This class provides methods for FastAPI dependency injection to extract
    tenant ID, user ID, and validate API keys or JWT tokens.
    """

    def __init__(
        self,
        jwt_handler: JWTHandler,
        api_key_handler: APIKeyHandler,
        api_key_header: str = "X-API-Key",
    ) -> None:
        """Initialize authentication handler.

        Args:
            jwt_handler: JWT handler instance.
            api_key_handler: API key handler instance.
            api_key_header: Header name for API key.
        """
        self.jwt_handler = jwt_handler
        self.api_key_handler = api_key_handler
        self.api_key_header = api_key_header

    def extract_tenant_from_request(self, request: Request) -> str:
        """Extract tenant ID from request.

        Tries to extract tenant from:
        1. JWT token in Authorization header
        2. API key in X-API-Key header

        Args:
            request: FastAPI request object.

        Returns:
            str: Tenant identifier.

        Raises:
            HTTPException: If tenant cannot be extracted.
        """
        # Try JWT first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                tenant_id = self.jwt_handler.extract_tenant_id(token)
                if tenant_id:
                    return tenant_id
            except ValidationError:
                pass

        # Try API key
        api_key = request.headers.get(self.api_key_header)
        if api_key:
            # For API key, we extract tenant from the key prefix
            # In production, you'd look up the key in the database
            # For now, we try to parse it from the key format
            tenant_id = self._extract_tenant_from_api_key(api_key)
            if tenant_id:
                return tenant_id

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to extract tenant from request",
        )

    def _extract_tenant_from_api_key(self, api_key: str) -> Optional[str]:
        """Extract tenant ID from API key prefix.

        Args:
            api_key: API key string.

        Returns:
            Optional[str]: Tenant ID if extractable, None otherwise.
        """
        if not api_key:
            return None

        parts = api_key.split("_")
        if len(parts) >= 2:
            # Format: qk_{tenant_id}_{token}
            # Or: qk_{prefix}_{token}
            # For now, try to parse the second part
            try:
                # This is a simplistic extraction; real implementation
                # would validate against the database
                tenant_part = parts[1]
                if len(tenant_part) >= 8:
                    return tenant_part
            except (IndexError, ValueError):
                pass

        return None

    async def get_current_tenant(self, request: Request) -> str:
        """Dependency injection for current tenant.

        Args:
            request: FastAPI request.

        Returns:
            str: Tenant ID.

        Raises:
            HTTPException: If authentication fails.
        """
        return self.extract_tenant_from_request(request)

    async def get_current_user(self, request: Request) -> Optional[str]:
        """Dependency injection for current user.

        Args:
            request: FastAPI request.

        Returns:
            Optional[str]: User ID if authenticated.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        try:
            return self.jwt_handler.extract_user_id(token)
        except ValidationError:
            return None

    async def validate_api_key(self, request: Request) -> bool:
        """Validate API key from request.

        Args:
            request: FastAPI request.

        Returns:
            bool: True if API key is valid.

        Raises:
            HTTPException: If validation fails.
        """
        api_key = request.headers.get(self.api_key_header)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing {self.api_key_header} header",
            )

        # In production, validate against database
        # This is a placeholder validation
        if len(api_key) < 16:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        return True