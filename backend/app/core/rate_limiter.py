"""
In-memory rate limiter using the Token Bucket algorithm.

Features:
  - Per-IP tracking
  - Configurable limits per endpoint
  - FastAPI middleware integration
  - Returns 429 with Retry-After header when exceeded
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token Bucket implementation
# ---------------------------------------------------------------------------


@dataclass
class TokenBucket:
    """A single token bucket for one client/endpoint pair."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        self.tokens = self.capacity

    def consume(self, tokens: float = 1.0) -> Tuple[bool, float]:
        """
        Try to consume tokens.

        Returns:
            (allowed, retry_after_seconds)
            If allowed=True, tokens were consumed.
            If allowed=False, retry_after is how long until a token is available.
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.last_refill = now

        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        else:
            # Calculate how long until enough tokens are available
            deficit = tokens - self.tokens
            retry_after = deficit / self.refill_rate if self.refill_rate > 0 else 60.0
            return False, retry_after


# ---------------------------------------------------------------------------
# Rate Limiter Store
# ---------------------------------------------------------------------------


@dataclass
class EndpointConfig:
    """Rate limit configuration for a specific endpoint pattern."""

    capacity: int = 20  # max burst tokens
    refill_rate: float = 0.5  # tokens per second (e.g., 0.5 = 1 request per 2 seconds)


class RateLimiterStore:
    """
    Thread-safe in-memory store for per-IP token buckets.

    Supports different rate limits per endpoint prefix.
    """

    def __init__(
        self,
        default_capacity: int = 20,
        default_refill_rate: float = 0.5,
        cleanup_interval: int = 300,
    ):
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self.cleanup_interval = cleanup_interval

        # Key: (ip, endpoint_prefix) -> TokenBucket
        self._buckets: Dict[Tuple[str, str], TokenBucket] = {}

        # Endpoint-specific configs. Key: path prefix
        self._endpoint_configs: Dict[str, EndpointConfig] = {}

        self._last_cleanup = time.monotonic()

    def configure_endpoint(self, path_prefix: str, capacity: int, refill_rate: float):
        """Set rate limit for a specific endpoint prefix."""
        self._endpoint_configs[path_prefix] = EndpointConfig(
            capacity=capacity,
            refill_rate=refill_rate,
        )
        logger.info(
            "Rate limit configured: %s -> capacity=%d, refill=%.2f/s",
            path_prefix,
            capacity,
            refill_rate,
        )

    def _get_config(self, path: str) -> EndpointConfig:
        """Find the most specific endpoint config matching the path."""
        best_match = ""
        for prefix in self._endpoint_configs:
            if path.startswith(prefix) and len(prefix) > len(best_match):
                best_match = prefix

        if best_match:
            return self._endpoint_configs[best_match]

        return EndpointConfig(
            capacity=self.default_capacity,
            refill_rate=self.default_refill_rate,
        )

    def check(self, ip: str, path: str) -> Tuple[bool, float, int]:
        """
        Check if the request is allowed.

        Returns:
            (allowed, retry_after_seconds, remaining_tokens)
        """
        self._maybe_cleanup()

        config = self._get_config(path)

        # Use endpoint prefix for bucket key (group similar endpoints)
        endpoint_key = path
        for prefix in self._endpoint_configs:
            if path.startswith(prefix):
                endpoint_key = prefix
                break

        bucket_key = (ip, endpoint_key)

        if bucket_key not in self._buckets:
            self._buckets[bucket_key] = TokenBucket(
                capacity=config.capacity,
                refill_rate=config.refill_rate,
            )

        bucket = self._buckets[bucket_key]
        allowed, retry_after = bucket.consume(1.0)
        remaining = max(0, int(bucket.tokens))

        return allowed, retry_after, remaining

    def _maybe_cleanup(self):
        """Remove stale buckets periodically."""
        now = time.monotonic()
        if now - self._last_cleanup < self.cleanup_interval:
            return

        self._last_cleanup = now
        stale_threshold = now - self.cleanup_interval * 2
        stale_keys = [
            key for key, bucket in self._buckets.items() if bucket.last_refill < stale_threshold
        ]
        for key in stale_keys:
            del self._buckets[key]

        if stale_keys:
            logger.debug("Cleaned up %d stale rate-limit buckets", len(stale_keys))


# ---------------------------------------------------------------------------
# Global store singleton
# ---------------------------------------------------------------------------

_store: Optional[RateLimiterStore] = None


def get_rate_limiter_store() -> RateLimiterStore:
    """Get or create the global rate limiter store."""
    global _store
    if _store is None:
        from app.core.config import settings

        _store = RateLimiterStore(
            default_capacity=settings.RATE_LIMIT_REQUESTS,
            default_refill_rate=settings.RATE_LIMIT_REQUESTS
            / max(settings.RATE_LIMIT_WINDOW_SECONDS, 1),
        )
        # Configure endpoint-specific limits
        _store.configure_endpoint(
            "/api/v1/detect", capacity=settings.RATE_LIMIT_BURST, refill_rate=0.1
        )
        _store.configure_endpoint(
            "/api/v1/plagiarism", capacity=settings.RATE_LIMIT_BURST, refill_rate=0.1
        )
        _store.configure_endpoint(
            "/api/v1/humanize", capacity=settings.RATE_LIMIT_BURST, refill_rate=0.05
        )
        _store.configure_endpoint("/ws/detect", capacity=settings.RATE_LIMIT_BURST, refill_rate=0.2)
        _store.configure_endpoint("/api/v1/health", capacity=60, refill_rate=1.0)
    return _store


# ---------------------------------------------------------------------------
# Paths to skip rate limiting
# ---------------------------------------------------------------------------

SKIP_PATHS = {
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
    "/favicon.ico",
}


# ---------------------------------------------------------------------------
# FastAPI Middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that applies rate limiting based on the Token Bucket
    algorithm.  Returns 429 Too Many Requests with a Retry-After header
    when the limit is exceeded.
    """

    def __init__(self, app: ASGIApp, store: Optional[RateLimiterStore] = None):
        super().__init__(app)
        self.store = store or get_rate_limiter_store()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        # Skip rate limiting for docs and static paths
        if path in SKIP_PATHS:
            return await call_next(request)

        # Extract client IP
        ip = self._get_client_ip(request)

        # Check rate limit
        allowed, retry_after, remaining = self.store.check(ip, path)

        if not allowed:
            retry_after_int = max(1, int(retry_after) + 1)
            logger.warning(
                "Rate limit exceeded: ip=%s path=%s retry_after=%ds",
                ip,
                path,
                retry_after_int,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": retry_after_int,
                },
                headers={
                    "Retry-After": str(retry_after_int),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Proceed with the request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract the client IP, respecting X-Forwarded-For."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


def add_rate_limiting(app: FastAPI, store: Optional[RateLimiterStore] = None):
    """Convenience function to add rate limiting middleware to a FastAPI app."""
    app.add_middleware(RateLimitMiddleware, store=store)
    logger.info("Rate limiting middleware enabled")
