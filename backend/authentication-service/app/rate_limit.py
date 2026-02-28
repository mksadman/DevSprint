import redis as redis_lib

from app.config import settings


def get_redis_client() -> redis_lib.Redis:
    """Return a Redis client built from REDIS_HOST and REDIS_PORT."""
    return redis_lib.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2,
    )


def is_rate_limited(student_id: str) -> bool:
    """
    Increment the per-student login attempt counter.

    Returns True (block the request) when the student has exceeded
    RATE_LIMIT_MAX_ATTEMPTS within the RATE_LIMIT_WINDOW_SECONDS window.
    Fails open — if Redis is unreachable the request is allowed through.
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
        return False
