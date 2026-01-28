"""Minimal mock API server for testing."""

import asyncio
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock Server", version="0.1.0")


@dataclass
class TokenBucket:
    """Token bucket rate limiter."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        self.tokens = self.capacity

    def consume(self, tokens: float = 1.0) -> tuple[bool, float]:
        """Try to consume tokens. Returns (allowed, retry_after_seconds)."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        else:
            wait_time = (tokens - self.tokens) / self.refill_rate
            return False, wait_time


# Rate limiters by bucket name (client IP + bucket name)
_rate_limiters: dict[str, TokenBucket] = {}


def get_limiter(key: str, capacity: float, refill_rate: float) -> TokenBucket:
    """Get or create a rate limiter for the given key."""
    if key not in _rate_limiters:
        _rate_limiters[key] = TokenBucket(capacity=capacity, refill_rate=refill_rate)
    return _rate_limiters[key]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route("/echo", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def echo(request: Request):
    """Returns request details."""
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = (await request.body()).decode("utf-8", errors="replace")

    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "body": body,
        "client": request.client.host if request.client else None,
        "timestamp": time.time(),
    }


@app.get("/status/{code}")
async def return_status(code: int):
    """Returns the specified HTTP status code."""
    if code < 100 or code > 599:
        return JSONResponse({"error": "Invalid status code"}, status_code=400)
    return Response(status_code=code)


@app.get("/delay/{ms}")
async def delay(ms: int):
    """Responds after specified delay in milliseconds."""
    if ms < 0:
        ms = 0
    if ms > 30000:
        ms = 30000
    await asyncio.sleep(ms / 1000)
    return {"delayed_ms": ms, "timestamp": time.time()}


@app.get("/random-error")
async def random_error(rate: float = 0.2):
    """Fails randomly at the given rate (0.0 to 1.0)."""
    rate = max(0.0, min(1.0, rate))
    if random.random() < rate:
        return JSONResponse(
            {"error": "Random failure", "rate": rate},
            status_code=500,
        )
    return {"success": True, "rate": rate}


@app.get("/data/{size}")
async def data(size: int):
    """Returns a response of approximately the specified size in bytes."""
    size = max(0, min(size, 1_000_000))
    payload = "x" * size
    return {"size": size, "data": payload}


@app.get("/headers")
async def headers(request: Request):
    """Returns request headers."""
    return {"headers": dict(request.headers)}


@app.api_route("/ratelimit", methods=["GET", "POST"])
async def ratelimit(request: Request, rps: float = 10.0, burst: float = 20.0):
    """
    Rate-limited endpoint using token bucket algorithm.

    Query params:
        rps: Requests per second allowed (default: 10)
        burst: Burst capacity (default: 20)

    Returns 429 with Retry-After header when rate exceeded.
    """
    rps = max(0.1, min(1000.0, rps))
    burst = max(1.0, min(1000.0, burst))

    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:ratelimit:{rps}:{burst}"

    limiter = get_limiter(key, capacity=burst, refill_rate=rps)
    allowed, retry_after = limiter.consume(1.0)

    if not allowed:
        return JSONResponse(
            {
                "error": "Rate limit exceeded",
                "retry_after": round(retry_after, 2),
                "limit_rps": rps,
                "burst": burst,
            },
            status_code=429,
            headers={"Retry-After": str(int(retry_after) + 1)},
        )

    return {
        "success": True,
        "tokens_remaining": round(limiter.tokens, 2),
        "limit_rps": rps,
        "burst": burst,
    }


@app.post("/ratelimit/reset")
async def ratelimit_reset():
    """Reset all rate limiters."""
    _rate_limiters.clear()
    return {"reset": True}


@app.get("/ratelimit/quota")
async def ratelimit_quota(limit: int = 100):
    """
    Global quota endpoint - shared across all clients.
    Simulates API daily/hourly quotas.

    Query params:
        limit: Total requests allowed (default: 100)

    Reset with POST /ratelimit/reset
    """
    limit = max(1, min(10000, limit))
    key = f"global:quota:{limit}"

    # Very slow refill (essentially no refill until reset)
    limiter = get_limiter(key, capacity=float(limit), refill_rate=0.001)
    allowed, _ = limiter.consume(1.0)

    remaining = max(0, int(limiter.tokens))

    if not allowed:
        return JSONResponse(
            {"error": "Quota exceeded", "limit": limit, "remaining": 0},
            status_code=429,
            headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"},
        )

    return {
        "success": True,
        "limit": limit,
        "remaining": remaining,
    }


@app.get("/ratelimit/status")
async def ratelimit_status():
    """Returns current state of all rate limiters."""
    return {
        "limiters": {
            k: {
                "tokens": round(v.tokens, 2),
                "capacity": v.capacity,
                "refill_rate": v.refill_rate,
            }
            for k, v in _rate_limiters.items()
        }
    }


@app.get("/ratelimit/strict/{rps}")
async def ratelimit_strict(request: Request, rps: int):
    """
    Strict rate limit with no burst (rps = burst).
    Useful for testing exact rate limit behavior.
    """
    rps = max(1, min(100, rps))

    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:strict:{rps}"

    limiter = get_limiter(key, capacity=float(rps), refill_rate=float(rps))
    allowed, retry_after = limiter.consume(1.0)

    if not allowed:
        return JSONResponse(
            {"error": "Rate limit exceeded", "retry_after": round(retry_after, 2)},
            status_code=429,
            headers={"Retry-After": str(int(retry_after) + 1)},
        )

    return {"success": True, "rps_limit": rps}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
