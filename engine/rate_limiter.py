"""Token bucket rate limiter for controlling request rate."""

import asyncio
import time


class TokenBucketRateLimiter:
    """Async token bucket rate limiter.

    Implements a token bucket algorithm where tokens are added at a fixed rate
    and each request consumes one token. If no tokens are available, the
    request waits until a token becomes available.

    Example:
        limiter = TokenBucketRateLimiter(rate=10.0)  # 10 requests per second
        async with limiter:
            await make_request()
    """

    def __init__(
        self,
        rate: float,
        burst: int | None = None,
    ):
        """Initialize the rate limiter.

        Args:
            rate: Maximum requests per second
            burst: Maximum burst size (defaults to rate)
        """
        self.rate = rate
        self.burst = burst if burst is not None else int(rate)
        self.tokens = float(self.burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary.

        This method blocks until a token is available.
        """
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now

                # Add tokens based on elapsed time
                self.tokens = min(
                    self.burst,
                    self.tokens + elapsed * self.rate
                )

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.rate

                # Release lock while waiting
                self._lock.release()
                try:
                    await asyncio.sleep(wait_time)
                finally:
                    await self._lock.acquire()

    async def __aenter__(self) -> "TokenBucketRateLimiter":
        """Async context manager entry - acquires a token."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        pass

    def reset(self) -> None:
        """Reset the rate limiter to full tokens."""
        self.tokens = float(self.burst)
        self.last_update = time.monotonic()


class NoopRateLimiter:
    """A rate limiter that doesn't limit - for unlimited request rates."""

    async def acquire(self) -> None:
        """No-op acquire."""
        pass

    async def __aenter__(self) -> "NoopRateLimiter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        pass

    def reset(self) -> None:
        """No-op reset."""
        pass
