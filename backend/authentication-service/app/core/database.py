import redis as redis_lib

from app.core.config import settings


def get_redis_client() -> redis_lib.Redis:
    """Return a Redis client built from REDIS_HOST and REDIS_PORT."""
    return redis_lib.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2,
    )
