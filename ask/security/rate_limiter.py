from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Token-bucket rate limiter for operation throttling."""

    def __init__(
        self,
        *,
        calls_per_second: float = 10.0,
        burst_size: int = 20,
        llm_calls_per_second: float = 1.0,
        llm_burst: int = 3,
    ) -> None:
        self._calls_per_second = max(0.1, calls_per_second)
        self._burst_size = max(1, burst_size)
        self._llm_calls_per_second = max(0.1, llm_calls_per_second)
        self._llm_burst = max(1, llm_burst)
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=float(burst_size), last_refill=time.monotonic())
        )
        self._llm_bucket = _Bucket(tokens=float(llm_burst), last_refill=time.monotonic())

    def check_command(self, key: str = "default") -> None:
        now = time.monotonic()
        bucket = self._buckets[key]
        elapsed = now - bucket.last_refill
        bucket.tokens = min(
            float(self._burst_size),
            bucket.tokens + elapsed * self._calls_per_second,
        )
        bucket.last_refill = now
        if bucket.tokens < 1.0:
            raise RateLimitError("Rate limit exceeded. Please wait before sending more commands.")
        bucket.tokens -= 1.0

    def check_llm_call(self) -> None:
        now = time.monotonic()
        elapsed = now - self._llm_bucket.last_refill
        self._llm_bucket.tokens = min(
            float(self._llm_burst),
            self._llm_bucket.tokens + elapsed * self._llm_calls_per_second,
        )
        self._llm_bucket.last_refill = now
        if self._llm_bucket.tokens < 1.0:
            raise RateLimitError("AI request rate limit exceeded. Please wait before sending more requests.")
        self._llm_bucket.tokens -= 1.0

    def reset(self) -> None:
        self._buckets.clear()
        self._llm_bucket = _Bucket(tokens=float(self._llm_burst), last_refill=time.monotonic())
