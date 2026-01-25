"""Authentication configuration models and providers."""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from engine.templating import TemplateEngine


class AuthType(str, Enum):
    """Supported authentication types."""

    BEARER_TOKEN = "bearer_token"
    API_KEY = "api_key"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"
    OAUTH2_PASSWORD_GRANT = "oauth2_password_grant"
    JWT = "jwt"


class BearerTokenAuth(BaseModel):
    """Bearer token authentication."""

    type: AuthType = AuthType.BEARER_TOKEN
    token: str = Field(..., description="Bearer token (supports template variables)")


class ApiKeyAuth(BaseModel):
    """API key authentication."""

    type: AuthType = AuthType.API_KEY
    key: str = Field(..., description="API key value (supports template variables)")
    header_name: str = Field(
        default="X-API-Key", description="Header name for the API key"
    )


class OAuth2ClientCredentials(BaseModel):
    """OAuth2 client credentials flow authentication."""

    type: AuthType = AuthType.OAUTH2_CLIENT_CREDENTIALS
    token_url: str = Field(..., description="Token endpoint URL")
    client_id: str = Field(..., description="Client ID")
    client_secret: str = Field(
        ..., description="Client secret (supports template variables)"
    )
    scope: str | None = Field(default=None, description="Space-separated scopes")


class OAuth2PasswordGrant(BaseModel):
    """OAuth2 password grant flow authentication."""

    type: AuthType = AuthType.OAUTH2_PASSWORD_GRANT
    token_url: str = Field(..., description="Token endpoint URL")
    client_id: str = Field(..., description="Client ID")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password (supports template variables)")
    scope: str | None = Field(default=None, description="Space-separated scopes")


class JWTAuth(BaseModel):
    """JWT token generation authentication."""

    type: AuthType = AuthType.JWT
    secret: str = Field(..., description="JWT signing secret (supports template variables)")
    algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    issuer: str | None = Field(default=None, description="JWT issuer (iss claim)")
    subject: str | None = Field(default=None, description="JWT subject (sub claim)")
    audience: str | None = Field(default=None, description="JWT audience (aud claim)")
    claims: dict[str, Any] = Field(
        default_factory=dict, description="Additional JWT claims"
    )
    expires_in_seconds: int = Field(
        default=3600, description="Token expiration time in seconds"
    )


AuthConfig = (
    BearerTokenAuth
    | ApiKeyAuth
    | OAuth2ClientCredentials
    | OAuth2PasswordGrant
    | JWTAuth
)


class TokenCache:
    """Async-safe cache for OAuth2 tokens with TTL.

    Caches tokens and automatically refreshes them when they expire.
    Thread-safe for concurrent access.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        """Get a cached token if not expired.

        Args:
            key: Cache key for the token

        Returns:
            Token value if cached and not expired, None otherwise
        """
        async with self._lock:
            if key in self._cache:
                token, expires_at = self._cache[key]
                if time.time() < expires_at:
                    return token
                del self._cache[key]
            return None

    async def set(self, key: str, token: str, expires_in: int) -> None:
        """Cache a token with TTL.

        Args:
            key: Cache key for the token
            token: Token value to cache
            expires_in: Time in seconds until token expires
        """
        async with self._lock:
            # Subtract a buffer to refresh before actual expiration
            buffer = min(30, expires_in // 10)
            expires_at = time.time() + expires_in - buffer
            self._cache[key] = (token, expires_at)

    async def clear(self, key: str | None = None) -> None:
        """Clear cached tokens.

        Args:
            key: Specific key to clear, or None to clear all
        """
        async with self._lock:
            if key is None:
                self._cache.clear()
            elif key in self._cache:
                del self._cache[key]


class AuthProvider:
    """Resolves authentication configuration to HTTP headers.

    Handles token substitution, OAuth2 flows, and JWT generation.
    Caches OAuth2 tokens for efficiency.
    """

    def __init__(
        self,
        template_engine: "TemplateEngine",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the auth provider.

        Args:
            template_engine: Template engine for variable substitution
            http_client: Optional HTTP client for OAuth2 flows
        """
        self._template_engine = template_engine
        self._external_client = http_client
        self._token_cache = TokenCache()

    async def get_headers(self, auth_config: AuthConfig) -> dict[str, str]:
        """Resolve auth config to HTTP headers.

        Args:
            auth_config: Authentication configuration

        Returns:
            Dictionary of HTTP headers to add to requests
        """
        if isinstance(auth_config, BearerTokenAuth):
            return self._get_bearer_headers(auth_config)
        elif isinstance(auth_config, ApiKeyAuth):
            return self._get_api_key_headers(auth_config)
        elif isinstance(auth_config, OAuth2ClientCredentials):
            return await self._get_oauth2_client_credentials_headers(auth_config)
        elif isinstance(auth_config, OAuth2PasswordGrant):
            return await self._get_oauth2_password_grant_headers(auth_config)
        elif isinstance(auth_config, JWTAuth):
            return self._get_jwt_headers(auth_config)
        else:
            raise ValueError(f"Unknown auth type: {type(auth_config)}")

    def _get_bearer_headers(self, auth_config: BearerTokenAuth) -> dict[str, str]:
        """Get headers for bearer token auth."""
        token = self._template_engine.substitute(auth_config.token)
        return {"Authorization": f"Bearer {token}"}

    def _get_api_key_headers(self, auth_config: ApiKeyAuth) -> dict[str, str]:
        """Get headers for API key auth."""
        key = self._template_engine.substitute(auth_config.key)
        header_name = self._template_engine.substitute(auth_config.header_name)
        return {header_name: key}

    async def _get_oauth2_client_credentials_headers(
        self, auth_config: OAuth2ClientCredentials
    ) -> dict[str, str]:
        """Get headers for OAuth2 client credentials flow."""
        # Build cache key from config
        cache_key = f"oauth2_cc:{auth_config.token_url}:{auth_config.client_id}"

        # Check cache
        cached_token = await self._token_cache.get(cache_key)
        if cached_token:
            return {"Authorization": f"Bearer {cached_token}"}

        # Request new token
        token_url = self._template_engine.substitute(auth_config.token_url)
        client_id = self._template_engine.substitute(auth_config.client_id)
        client_secret = self._template_engine.substitute(auth_config.client_secret)

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if auth_config.scope:
            data["scope"] = self._template_engine.substitute(auth_config.scope)

        token, expires_in = await self._fetch_oauth2_token(token_url, data)
        await self._token_cache.set(cache_key, token, expires_in)

        return {"Authorization": f"Bearer {token}"}

    async def _get_oauth2_password_grant_headers(
        self, auth_config: OAuth2PasswordGrant
    ) -> dict[str, str]:
        """Get headers for OAuth2 password grant flow."""
        # Build cache key from config
        cache_key = (
            f"oauth2_pw:{auth_config.token_url}:{auth_config.client_id}:"
            f"{auth_config.username}"
        )

        # Check cache
        cached_token = await self._token_cache.get(cache_key)
        if cached_token:
            return {"Authorization": f"Bearer {cached_token}"}

        # Request new token
        token_url = self._template_engine.substitute(auth_config.token_url)
        client_id = self._template_engine.substitute(auth_config.client_id)
        username = self._template_engine.substitute(auth_config.username)
        password = self._template_engine.substitute(auth_config.password)

        data = {
            "grant_type": "password",
            "client_id": client_id,
            "username": username,
            "password": password,
        }
        if auth_config.scope:
            data["scope"] = self._template_engine.substitute(auth_config.scope)

        token, expires_in = await self._fetch_oauth2_token(token_url, data)
        await self._token_cache.set(cache_key, token, expires_in)

        return {"Authorization": f"Bearer {token}"}

    async def _fetch_oauth2_token(
        self, token_url: str, data: dict[str, str]
    ) -> tuple[str, int]:
        """Fetch an OAuth2 token from the token endpoint.

        Args:
            token_url: Token endpoint URL
            data: Form data for token request

        Returns:
            Tuple of (access_token, expires_in_seconds)

        Raises:
            httpx.HTTPStatusError: If token request fails
            ValueError: If response is missing required fields
        """
        if self._external_client:
            client = self._external_client
            should_close = False
        else:
            client = httpx.AsyncClient()
            should_close = True

        try:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("OAuth2 response missing access_token")

            # Default to 1 hour if not specified
            expires_in = token_data.get("expires_in", 3600)
            return access_token, expires_in
        finally:
            if should_close:
                await client.aclose()

    def _get_jwt_headers(self, auth_config: JWTAuth) -> dict[str, str]:
        """Get headers for JWT auth."""
        try:
            import jwt
        except ImportError:
            raise ImportError(
                "PyJWT is required for JWT authentication. "
                "Install it with: pip install 'api-test-machine[auth]'"
            )

        secret = self._template_engine.substitute(auth_config.secret)

        # Build claims
        now = int(time.time())
        claims: dict[str, Any] = {
            "iat": now,
            "exp": now + auth_config.expires_in_seconds,
        }

        if auth_config.issuer:
            claims["iss"] = self._template_engine.substitute(auth_config.issuer)
        if auth_config.subject:
            claims["sub"] = self._template_engine.substitute(auth_config.subject)
        if auth_config.audience:
            claims["aud"] = self._template_engine.substitute(auth_config.audience)

        # Add custom claims
        for key, value in auth_config.claims.items():
            if isinstance(value, str):
                claims[key] = self._template_engine.substitute(value)
            else:
                claims[key] = value

        token = jwt.encode(claims, secret, algorithm=auth_config.algorithm)
        return {"Authorization": f"Bearer {token}"}


def parse_auth_config(data: dict[str, Any]) -> AuthConfig:
    """Parse a dictionary into the appropriate AuthConfig type.

    Args:
        data: Dictionary with auth configuration including 'type' field

    Returns:
        Appropriate AuthConfig subtype

    Raises:
        ValueError: If type is unknown or missing
    """
    auth_type = data.get("type")
    if not auth_type:
        raise ValueError("Auth config missing 'type' field")

    type_map: dict[str, type[AuthConfig]] = {
        AuthType.BEARER_TOKEN.value: BearerTokenAuth,
        AuthType.API_KEY.value: ApiKeyAuth,
        AuthType.OAUTH2_CLIENT_CREDENTIALS.value: OAuth2ClientCredentials,
        AuthType.OAUTH2_PASSWORD_GRANT.value: OAuth2PasswordGrant,
        AuthType.JWT.value: JWTAuth,
    }

    config_class = type_map.get(auth_type)
    if not config_class:
        raise ValueError(f"Unknown auth type: {auth_type}")

    return config_class(**data)
