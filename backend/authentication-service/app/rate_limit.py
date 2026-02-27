import redis as redis_lib

from app.config import settings


def get_redis_client() -> redis_lib.Redis:
    """Return a Redis client using the configured URL."""
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def is_rate_limited(student_id: str) -> bool:
    """
    Increment the attempt counter for the given student_id.

    Returns True (request should be blocked) when the student has exceeded
    RATE_LIMIT_MAX_ATTEMPTS within the RATE_LIMIT_WINDOW_SECONDS window.
    The counter key expires automatically after the window so the bucket resets.
    """
    try:
        client = get_redis_client()
        key = f"rl:login:{student_id}"

        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
        results = pipe.execute()

        attempt_count: int = results[0]
        return attempt_count > settings.RATE_LIMIT_MAX_ATTEMPTS
    except redis_lib.RedisError:
        # Fail open: if Redis is unreachable, do not block the request.
        return False
