"""
TalentPulse AI - Security & Rate Limiting Module (Layer 2 Defense)
Protects against API quota abuse, bot spamming, and denial-of-service attacks.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status

logger = logging.getLogger("talentpulse.security")

class SlidingWindowRateLimiter:
    """
    In-memory Sliding Window Rate Limiter.
    Limits requests per IP / User identifier within a rolling time window.
    """
    def __init__(self):
        # Store timestamp logs: { "user_or_ip:route_tag": [t1, t2, ...] }
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(
        self,
        identifier: str,
        route_tag: str,
        max_requests: int = 5,
        window_seconds: int = 60
    ):
        """
        Check and record a request. Raises HTTP 429 if rate limit is exceeded.
        """
        now = time.time()
        key = f"{identifier}:{route_tag}"
        timestamps = self._history[key]

        # Prune timestamps older than window
        cutoff = now - window_seconds
        self._history[key] = [t for t in timestamps if t > cutoff]

        if len(self._history[key]) >= max_requests:
            retry_after = int(window_seconds - (now - self._history[key][0])) + 1
            logger.warning(f"Rate limit exceeded for {identifier} on [{route_tag}]. Blocked for {retry_after}s.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. You can only perform {max_requests} requests per minute on {route_tag}. Please retry in {retry_after} seconds.",
                headers={"Retry-After": str(max(1, retry_after))}
            )

        # Record this request timestamp
        self._history[key].append(now)

rate_limiter = SlidingWindowRateLimiter()

def get_client_ip(request: Request) -> str:
    """Extract real client IP address considering proxy headers."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
