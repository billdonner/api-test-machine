"""Tests for rate limiter."""

import asyncio
import time

import pytest

from engine.rate_limiter import NoopRateLimiter, TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    @pytest.mark.asyncio
    async def test_allows_burst(self):
        """Test that burst requests are allowed immediately."""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5)

        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Burst should complete almost immediately
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limits_after_burst(self):
        """Test that rate limiting kicks in after burst."""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=2)

        start = time.monotonic()
        # First 2 should be immediate (burst)
        await limiter.acquire()
        await limiter.acquire()
        # Third should wait ~0.1s (at 10 req/s)
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should take at least 0.08s for the third request
        assert elapsed >= 0.08

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        limiter = TokenBucketRateLimiter(rate=100.0)

        async with limiter:
            pass  # Token acquired

        # Should work without errors

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test reset restores tokens."""
        limiter = TokenBucketRateLimiter(rate=1.0, burst=1)

        await limiter.acquire()  # Use the token
        limiter.reset()  # Restore tokens

        start = time.monotonic()
        await limiter.acquire()  # Should be immediate now
        elapsed = time.monotonic() - start

        assert elapsed < 0.1


class TestNoopRateLimiter:
    """Tests for NoopRateLimiter."""

    @pytest.mark.asyncio
    async def test_no_limiting(self):
        """Test that NoopRateLimiter doesn't limit."""
        limiter = NoopRateLimiter()

        start = time.monotonic()
        for _ in range(100):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should complete almost immediately
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        limiter = NoopRateLimiter()

        async with limiter:
            pass  # No limiting
