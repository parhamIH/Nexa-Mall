import redis

from django.conf import settings


def get_redis_client():
    """
    Raw redis-py client for commands the Django cache API does not
    expose (e.g. token-owned locks). Points at the same Redis
    instance as the default cache backend.
    """
    location = settings.CACHES["default"]["LOCATION"]

    return redis.Redis.from_url(
        location,
        decode_responses=True,
    )
