"""API key authentication for the Control API."""

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status


def get_api_key() -> str | None:
    """Get the configured API key from environment.

    Returns:
        The API key or None if not configured
    """
    return os.environ.get("API_TEST_MACHINE_API_KEY")


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> str:
    """Verify the API key from request header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The verified API key

    Raises:
        HTTPException: If key is missing or invalid
    """
    expected_key = get_api_key()

    # If no API key is configured, allow all requests (dev mode)
    if expected_key is None:
        return "dev-mode"

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return x_api_key


# Dependency for protected routes
ApiKeyDep = Annotated[str, Depends(verify_api_key)]
