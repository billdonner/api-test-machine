"""Tests for authentication module."""

import asyncio
import time

import httpx
import pytest

from engine.auth import (
    ApiKeyAuth,
    AuthProvider,
    AuthType,
    BearerTokenAuth,
    JWTAuth,
    OAuth2ClientCredentials,
    OAuth2PasswordGrant,
    TokenCache,
    parse_auth_config,
)
from engine.templating import TemplateEngine


class TestBearerTokenAuth:
    """Tests for bearer token authentication."""

    @pytest.mark.asyncio
    async def test_bearer_token_header(self):
        """Test bearer token generates correct header."""
        auth = BearerTokenAuth(token="test-token-123")
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        assert headers == {"Authorization": "Bearer test-token-123"}

    @pytest.mark.asyncio
    async def test_bearer_token_with_template(self, monkeypatch):
        """Test bearer token supports template variables."""
        monkeypatch.setenv("API_TOKEN", "secret-from-env")

        auth = BearerTokenAuth(token="{{env:API_TOKEN}}")
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        assert headers == {"Authorization": "Bearer secret-from-env"}

    @pytest.mark.asyncio
    async def test_bearer_token_with_custom_variable(self):
        """Test bearer token with custom variables."""
        auth = BearerTokenAuth(token="{{my_token}}")
        template_engine = TemplateEngine(variables={"my_token": "custom-token"})
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        assert headers == {"Authorization": "Bearer custom-token"}


class TestApiKeyAuth:
    """Tests for API key authentication."""

    @pytest.mark.asyncio
    async def test_api_key_default_header(self):
        """Test API key with default header name."""
        auth = ApiKeyAuth(key="my-api-key")
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        assert headers == {"X-API-Key": "my-api-key"}

    @pytest.mark.asyncio
    async def test_api_key_custom_header(self):
        """Test API key with custom header name."""
        auth = ApiKeyAuth(key="my-api-key", header_name="Authorization")
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        assert headers == {"Authorization": "my-api-key"}

    @pytest.mark.asyncio
    async def test_api_key_with_template(self, monkeypatch):
        """Test API key supports template variables."""
        monkeypatch.setenv("SECRET_KEY", "key-from-env")

        auth = ApiKeyAuth(key="{{env:SECRET_KEY}}", header_name="X-Custom-Key")
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        assert headers == {"X-Custom-Key": "key-from-env"}


class MockOAuth2Transport(httpx.AsyncBaseTransport):
    """Mock transport for OAuth2 token endpoint."""

    def __init__(
        self,
        access_token: str = "mock-access-token",
        expires_in: int = 3600,
        status_code: int = 200,
    ):
        self.access_token = access_token
        self.expires_in = expires_in
        self.status_code = status_code
        self.request_count = 0
        self.last_request_data: dict[str, str] | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        # Parse form data
        body = request.content.decode()
        self.last_request_data = dict(
            item.split("=") for item in body.split("&") if "=" in item
        )

        if self.status_code != 200:
            return httpx.Response(self.status_code, content=b'{"error": "invalid"}')

        content = (
            f'{{"access_token": "{self.access_token}", '
            f'"token_type": "bearer", '
            f'"expires_in": {self.expires_in}}}'
        )
        return httpx.Response(200, content=content.encode())


class TestOAuth2ClientCredentials:
    """Tests for OAuth2 client credentials flow."""

    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_flow(self):
        """Test OAuth2 client credentials fetches token."""
        transport = MockOAuth2Transport(access_token="cc-token-123")
        client = httpx.AsyncClient(transport=transport)

        auth = OAuth2ClientCredentials(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine, http_client=client)

        headers = await provider.get_headers(auth)

        assert headers == {"Authorization": "Bearer cc-token-123"}
        assert transport.request_count == 1
        assert transport.last_request_data["grant_type"] == "client_credentials"
        assert transport.last_request_data["client_id"] == "my-client"
        assert transport.last_request_data["client_secret"] == "my-secret"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_with_scope(self):
        """Test OAuth2 client credentials with scope."""
        transport = MockOAuth2Transport()
        client = httpx.AsyncClient(transport=transport)

        auth = OAuth2ClientCredentials(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
            scope="read write",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine, http_client=client)

        await provider.get_headers(auth)

        assert transport.last_request_data["scope"] == "read+write"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_caching(self):
        """Test OAuth2 tokens are cached."""
        transport = MockOAuth2Transport(access_token="cached-token", expires_in=3600)
        client = httpx.AsyncClient(transport=transport)

        auth = OAuth2ClientCredentials(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine, http_client=client)

        # First call should fetch token
        headers1 = await provider.get_headers(auth)
        assert transport.request_count == 1

        # Second call should use cache
        headers2 = await provider.get_headers(auth)
        assert transport.request_count == 1  # No additional request

        assert headers1 == headers2 == {"Authorization": "Bearer cached-token"}

        await client.aclose()

    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_template_substitution(self, monkeypatch):
        """Test OAuth2 supports template variables."""
        monkeypatch.setenv("CLIENT_SECRET", "env-secret")

        transport = MockOAuth2Transport()
        client = httpx.AsyncClient(transport=transport)

        auth = OAuth2ClientCredentials(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="{{env:CLIENT_SECRET}}",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine, http_client=client)

        await provider.get_headers(auth)

        assert transport.last_request_data["client_secret"] == "env-secret"

        await client.aclose()


class TestOAuth2PasswordGrant:
    """Tests for OAuth2 password grant flow."""

    @pytest.mark.asyncio
    async def test_oauth2_password_grant_flow(self):
        """Test OAuth2 password grant fetches token."""
        transport = MockOAuth2Transport(access_token="pw-token-456")
        client = httpx.AsyncClient(transport=transport)

        auth = OAuth2PasswordGrant(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            username="testuser",
            password="testpass",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine, http_client=client)

        headers = await provider.get_headers(auth)

        assert headers == {"Authorization": "Bearer pw-token-456"}
        assert transport.request_count == 1
        assert transport.last_request_data["grant_type"] == "password"
        assert transport.last_request_data["client_id"] == "my-client"
        assert transport.last_request_data["username"] == "testuser"
        assert transport.last_request_data["password"] == "testpass"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_oauth2_password_grant_with_scope(self):
        """Test OAuth2 password grant with scope."""
        transport = MockOAuth2Transport()
        client = httpx.AsyncClient(transport=transport)

        auth = OAuth2PasswordGrant(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            username="testuser",
            password="testpass",
            scope="admin",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine, http_client=client)

        await provider.get_headers(auth)

        assert transport.last_request_data["scope"] == "admin"

        await client.aclose()


class TestTokenCache:
    """Tests for token caching."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test cache stores and retrieves tokens."""
        cache = TokenCache()

        await cache.set("key1", "token1", expires_in=3600)
        result = await cache.get("key1")

        assert result == "token1"

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test expired tokens are not returned."""
        cache = TokenCache()

        # Set with short expiration
        # Buffer is min(30, 60//10) = 6, so expires_at = now + 60 - 6 = now + 54
        # We'll manually manipulate the cache to test expiration
        await cache.set("key1", "token1", expires_in=60)

        # Manually set a past expiration time
        async with cache._lock:
            cache._cache["key1"] = ("token1", time.time() - 1)

        # Token should be expired now
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test missing keys return None."""
        cache = TokenCache()

        result = await cache.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_clear_specific_key(self):
        """Test clearing a specific key."""
        cache = TokenCache()

        await cache.set("key1", "token1", expires_in=3600)
        await cache.set("key2", "token2", expires_in=3600)

        await cache.clear("key1")

        assert await cache.get("key1") is None
        assert await cache.get("key2") == "token2"

    @pytest.mark.asyncio
    async def test_cache_clear_all(self):
        """Test clearing all keys."""
        cache = TokenCache()

        await cache.set("key1", "token1", expires_in=3600)
        await cache.set("key2", "token2", expires_in=3600)

        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None


class TestJWTAuth:
    """Tests for JWT authentication."""

    @pytest.mark.asyncio
    async def test_jwt_basic_generation(self):
        """Test JWT generates valid token."""
        pytest.importorskip("jwt")
        import jwt

        auth = JWTAuth(
            secret="test-secret",
            algorithm="HS256",
            expires_in_seconds=300,
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")

        # Decode and verify token
        token = headers["Authorization"].split(" ")[1]
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])

        assert "iat" in decoded
        assert "exp" in decoded
        assert decoded["exp"] - decoded["iat"] == 300

    @pytest.mark.asyncio
    async def test_jwt_with_claims(self):
        """Test JWT includes standard claims."""
        pytest.importorskip("jwt")
        import jwt

        auth = JWTAuth(
            secret="test-secret",
            algorithm="HS256",
            issuer="api-test-machine",
            subject="test-user",
            audience="api-server",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        token = headers["Authorization"].split(" ")[1]
        decoded = jwt.decode(
            token,
            "test-secret",
            algorithms=["HS256"],
            audience="api-server",
        )

        assert decoded["iss"] == "api-test-machine"
        assert decoded["sub"] == "test-user"
        assert decoded["aud"] == "api-server"

    @pytest.mark.asyncio
    async def test_jwt_with_custom_claims(self):
        """Test JWT includes custom claims."""
        pytest.importorskip("jwt")
        import jwt

        auth = JWTAuth(
            secret="test-secret",
            algorithm="HS256",
            claims={"role": "admin", "tenant_id": 123},
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        token = headers["Authorization"].split(" ")[1]
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])

        assert decoded["role"] == "admin"
        assert decoded["tenant_id"] == 123

    @pytest.mark.asyncio
    async def test_jwt_template_substitution(self, monkeypatch):
        """Test JWT supports template variables."""
        pytest.importorskip("jwt")
        import jwt

        monkeypatch.setenv("JWT_SECRET", "secret-from-env")

        auth = JWTAuth(
            secret="{{env:JWT_SECRET}}",
            algorithm="HS256",
        )
        template_engine = TemplateEngine()
        provider = AuthProvider(template_engine=template_engine)

        headers = await provider.get_headers(auth)

        token = headers["Authorization"].split(" ")[1]
        # Verify it was signed with the env secret
        decoded = jwt.decode(token, "secret-from-env", algorithms=["HS256"])
        assert decoded is not None


class TestParseAuthConfig:
    """Tests for auth config parsing."""

    def test_parse_bearer_token(self):
        """Test parsing bearer token config."""
        data = {"type": "bearer_token", "token": "my-token"}
        config = parse_auth_config(data)

        assert isinstance(config, BearerTokenAuth)
        assert config.token == "my-token"

    def test_parse_api_key(self):
        """Test parsing API key config."""
        data = {"type": "api_key", "key": "my-key", "header_name": "X-Custom"}
        config = parse_auth_config(data)

        assert isinstance(config, ApiKeyAuth)
        assert config.key == "my-key"
        assert config.header_name == "X-Custom"

    def test_parse_oauth2_client_credentials(self):
        """Test parsing OAuth2 client credentials config."""
        data = {
            "type": "oauth2_client_credentials",
            "token_url": "https://auth.example.com/token",
            "client_id": "my-client",
            "client_secret": "my-secret",
            "scope": "read write",
        }
        config = parse_auth_config(data)

        assert isinstance(config, OAuth2ClientCredentials)
        assert config.token_url == "https://auth.example.com/token"
        assert config.scope == "read write"

    def test_parse_oauth2_password_grant(self):
        """Test parsing OAuth2 password grant config."""
        data = {
            "type": "oauth2_password_grant",
            "token_url": "https://auth.example.com/token",
            "client_id": "my-client",
            "username": "user",
            "password": "pass",
        }
        config = parse_auth_config(data)

        assert isinstance(config, OAuth2PasswordGrant)
        assert config.username == "user"

    def test_parse_jwt(self):
        """Test parsing JWT config."""
        data = {
            "type": "jwt",
            "secret": "my-secret",
            "algorithm": "HS512",
            "issuer": "my-app",
            "expires_in_seconds": 600,
        }
        config = parse_auth_config(data)

        assert isinstance(config, JWTAuth)
        assert config.algorithm == "HS512"
        assert config.issuer == "my-app"
        assert config.expires_in_seconds == 600

    def test_parse_missing_type(self):
        """Test error when type is missing."""
        with pytest.raises(ValueError, match="missing 'type' field"):
            parse_auth_config({"token": "test"})

    def test_parse_unknown_type(self):
        """Test error when type is unknown."""
        with pytest.raises(ValueError, match="Unknown auth type"):
            parse_auth_config({"type": "unknown_auth"})


class TestExecutorIntegration:
    """Tests for executor integration with auth."""

    @pytest.mark.asyncio
    async def test_executor_with_bearer_auth(self):
        """Test executor adds auth headers to requests."""
        from engine.executor import TestExecutor
        from engine.models import TestSpec

        class AuthCheckTransport(httpx.AsyncBaseTransport):
            def __init__(self):
                self.captured_headers: dict[str, str] = {}

            async def handle_async_request(
                self, request: httpx.Request
            ) -> httpx.Response:
                self.captured_headers = dict(request.headers)
                return httpx.Response(200, content=b'{"status": "ok"}')

        transport = AuthCheckTransport()
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="Auth Test",
            url="https://api.example.com/data",
            total_requests=1,
            concurrency=1,
            auth=BearerTokenAuth(token="test-bearer-token"),
        )

        await executor.run(spec)

        assert "authorization" in transport.captured_headers
        assert transport.captured_headers["authorization"] == "Bearer test-bearer-token"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_executor_auth_headers_merged_with_spec_headers(self):
        """Test auth headers are merged with spec headers (spec takes precedence)."""
        from engine.executor import TestExecutor
        from engine.models import TestSpec

        class HeaderCheckTransport(httpx.AsyncBaseTransport):
            def __init__(self):
                self.captured_headers: dict[str, str] = {}

            async def handle_async_request(
                self, request: httpx.Request
            ) -> httpx.Response:
                self.captured_headers = dict(request.headers)
                return httpx.Response(200, content=b'{"status": "ok"}')

        transport = HeaderCheckTransport()
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="Auth Test",
            url="https://api.example.com/data",
            total_requests=1,
            concurrency=1,
            headers={"X-Custom": "custom-value", "Content-Type": "application/json"},
            auth=BearerTokenAuth(token="test-token"),
        )

        await executor.run(spec)

        assert transport.captured_headers["authorization"] == "Bearer test-token"
        assert transport.captured_headers["x-custom"] == "custom-value"
        assert transport.captured_headers["content-type"] == "application/json"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_executor_without_auth(self):
        """Test executor works without auth config."""
        from engine.executor import TestExecutor
        from engine.models import RunStatus, TestSpec

        class SimpleTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(
                self, request: httpx.Request
            ) -> httpx.Response:
                return httpx.Response(200, content=b'{"status": "ok"}')

        transport = SimpleTransport()
        client = httpx.AsyncClient(transport=transport)

        executor = TestExecutor(http_client=client)
        spec = TestSpec(
            name="No Auth Test",
            url="https://api.example.com/data",
            total_requests=5,
            concurrency=1,
        )

        result = await executor.run(spec)

        assert result.status == RunStatus.COMPLETED
        assert result.metrics.successful_requests == 5

        await client.aclose()
