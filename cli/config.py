"""Environment-based configuration for the CLI."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """CLI configuration loaded from environment variables."""

    api_url: str
    api_key: str | None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Environment variables:
            ATM_API_URL: API server URL (default: http://localhost:8000)
            ATM_API_KEY: API key for authentication (optional in dev mode)

        Returns:
            Config instance
        """
        return cls(
            api_url=os.environ.get("ATM_API_URL", "http://localhost:8000"),
            api_key=os.environ.get("ATM_API_KEY"),
        )

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Dictionary of headers including API key if configured
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def get_api_endpoint(self, path: str) -> str:
        """Get full URL for an API endpoint.

        Args:
            path: API path (e.g., "/api/v1/runs")

        Returns:
            Full URL
        """
        base = self.api_url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"
