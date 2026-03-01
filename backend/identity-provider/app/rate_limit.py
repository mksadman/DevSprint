"""
Redis-backed fixed-window rate limiter for the authentication service.

Key format : login_attempts:{student_id}
Algorithm  : Fixed-window counter — the window starts on the first attempt
             and expires automatically after RATE_LIMIT_WINDOW_SECONDS.

Failure policy: FAIL OPEN — if Redis is unavailable the caller is allowed
through, a warning is logged, and the request proceeds normally.
"""

import logging

import redis as redis_lib

from app.core.config import settings
from app.core.database import get_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "login_attempts"


def is_rate_limited(student_id: str) -> bool:
    """
    Increment the per-student fixed-window login attempt counter.

    Each call atomically:
      1. INCRements  ``login_attempts:{student_id}``
      2. Sets EXPIRE only if the key has no TTL yet (``nx=True``), so the
         60-second window begins on the *first* attempt and is never
         accidentally extended by subsequent calls within the same window.

    Returns
    -------
    True  — the student has exceeded RATE_LIMIT_MAX_ATTEMPTS and the
            request must be blocked (HTTP 429).
    False — the request may proceed, OR Redis was unavailable (fail-open).
    """
    key = f"{_KEY_PREFIX}:{student_id}"

    try:
        client = get_redis_client()
        pipe = client.pipeline()
        pipe.incr(key)
        # nx=True: set expiry *only* when the key has no TTL (i.e. first incr).
        # This preserves the original window start on every subsequent attempt.
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS, nx=True)
        results = pipe.execute()

        attempt_count: int = results[0]
        return attempt_count > settings.RATE_LIMIT_MAX_ATTEMPTS

    except redis_lib.RedisError as exc:
        logger.warning(
            "Redis unavailable during rate-limit check for student_id=%r — "
            "failing open and allowing the request: %s",
            student_id,
            exc,
        )
        return False
