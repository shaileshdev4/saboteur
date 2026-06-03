"""Rate limiting.

We use SlowAPI (a FastAPI integration of the `limits` library). Per-IP limits
are sensible defaults; specific endpoints can declare tighter limits.

Why per-IP and not per-session?
  - Session creation is cheap (one POST), so per-session limits are trivially
    bypassable.
  - For real abuse prevention we'd need fingerprinting; that's V5+.

Limits chosen with the API doc:
  /audit: 60/hour
  /image/transcribe: 30/hour
  /class, /match (create/join): 30/hour
  Everything else: 240/hour (4/min average -plenty for normal play)

If SlowAPI isn't installed, we ship a no-op limiter so the app still runs.
"""
from __future__ import annotations

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    _HAS_SLOWAPI = True
except ImportError:
    _HAS_SLOWAPI = False


if _HAS_SLOWAPI:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["240/hour"],
        # In-memory storage. For multi-instance deploys, switch to Redis.
        storage_uri="memory://",
    )

    def install(app) -> None:
        """Attach SlowAPI to the FastAPI app."""
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

else:
    # No-op shim so endpoints can still decorate with @limiter.limit(...)
    # without crashing when SlowAPI isn't installed.
    class _NoopLimiter:
        def limit(self, *_args, **_kwargs):
            def decorator(fn):
                return fn
            return decorator

    limiter = _NoopLimiter()

    def install(app) -> None:
        pass
