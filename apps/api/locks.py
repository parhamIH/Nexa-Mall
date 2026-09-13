import uuid

from apps.api.redis import get_redis_client


# Compare-and-delete: release the lock only if we still own it.
# GET + DEL must happen atomically (Lua script), otherwise a lock
# that expired and was re-acquired by another worker could be
# deleted by its previous owner.
_RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class RedisLock:
    """
    Token-owned distributed lock.

    acquire(): SET key token NX EX timeout - a single atomic
    command; exactly one caller can win.

    release(): Lua compare-and-delete - only the current owner's
    token matches, so a worker whose lock expired (slow loader,
    crash) can never delete a lock that another worker now owns.

    The lock TTL (not to be confused with the cache TTL) is the
    crash-safety net: if the holder dies without releasing, the
    lock expires and the system keeps working.
    """

    def __init__(
        self,
        *,
        key,
        timeout=10,
    ):
        self.key = key
        self.timeout = timeout
        self.token = uuid.uuid4().hex

    def acquire(self):
        client = get_redis_client()

        return bool(
            client.set(
                self.key,
                self.token,
                nx=True,
                ex=self.timeout,
            )
        )

    def release(self):
        client = get_redis_client()

        return bool(
            client.eval(
                _RELEASE_LOCK_SCRIPT,
                1,
                self.key,
                self.token,
            )
        )
