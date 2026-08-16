import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, status

# In-memory fixed-window counter, keyed by "<key>:<client-ip>". Single-process
# only (see openspec/changes/add-password-auth/design.md) - a multi-worker
# deployment would need a shared store (e.g. Redis) instead.
_attempts: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(request: Request, key: str, limit: int, window_seconds: int) -> None:
    client_ip = request.client.host if request.client else "unknown"
    bucket_key = f"{key}:{client_ip}"
    now = time.monotonic()
    window_start = now - window_seconds

    attempts = [t for t in _attempts[bucket_key] if t > window_start]
    if len(attempts) >= limit:
        _attempts[bucket_key] = attempts
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, try again later",
        )
    attempts.append(now)
    _attempts[bucket_key] = attempts


def rate_limiter(key: str, limit: int = 10, window_seconds: int = 300) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        check_rate_limit(request, key, limit, window_seconds)

    return dependency


def reset_rate_limits() -> None:
    """Test-only: clears all counters so tests don't trip each other's limits."""
    _attempts.clear()
