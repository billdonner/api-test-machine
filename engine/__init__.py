"""Core async test execution engine."""

from engine.auth import (
    ApiKeyAuth,
    AuthConfig,
    AuthProvider,
    AuthType,
    BearerTokenAuth,
    JWTAuth,
    OAuth2ClientCredentials,
    OAuth2PasswordGrant,
    TokenCache,
    parse_auth_config,
)
from engine.executor import TestExecutor
from engine.metrics import MetricsCollector
from engine.models import Metrics, RunResult, RunStatus, TestSpec, Thresholds
from engine.rate_limiter import TokenBucketRateLimiter
from engine.templating import TemplateEngine

# Rebuild models to resolve forward references
TestSpec.model_rebuild()

__all__ = [
    # Models
    "TestSpec",
    "RunResult",
    "Metrics",
    "Thresholds",
    "RunStatus",
    # Auth
    "AuthType",
    "AuthConfig",
    "AuthProvider",
    "BearerTokenAuth",
    "ApiKeyAuth",
    "OAuth2ClientCredentials",
    "OAuth2PasswordGrant",
    "JWTAuth",
    "TokenCache",
    "parse_auth_config",
    # Execution
    "TestExecutor",
    "MetricsCollector",
    "TokenBucketRateLimiter",
    "TemplateEngine",
]
