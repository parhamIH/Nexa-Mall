import time
from collections.abc import Callable
from typing import Any

from django.core.cache import cache

from apps.api.locks import RedisLock


class AtomicCacheAside:
    """
    Cache-aside with single-flight (stampede) protection.

    GET / SET are each a single atomic Redis command, but the
    GET -> source -> SET chain is not atomic: without coordination,
    N concurrent misses would all hit the source at once (cache
    stampede / dogpile). Per key, only one worker performs the
    expensive fill while the others wait and re-read.

    The fill is guarded by a token-owned RedisLock: acquire is a
    single atomic SET NX EX command and release is an atomic Lua
    compare-and-delete, so a worker whose lock has expired can
    never delete a lock that is now owned by another worker.

    This is a cache lock (stampede protection) and deliberately NOT a
    database lock: state-changing races still belong to
    select_for_update() inside services.
    """

    RETRY_DELAY = 0.05
    MAX_RETRIES = 100

    def __init__(
        self,
        *,
        key: str,
        lock_key: str,
        timeout: int,
        lock_timeout: int = 10,
        set_loader_value: bool = True,
    ):
        self.key = key
        self.lock_key = lock_key
        self.timeout = timeout
        self.lock_timeout = lock_timeout

        # When the loader returns a sentinel (e.g. a negative-cache
        # marker that must be published with its own shorter TTL),
        # the caller publishes it itself and this helper must not
        # re-set it with the positive-data timeout.
        self.set_loader_value = set_loader_value

    def get(
        self,
        loader: Callable[[], Any],
    ):
        # -------------------------
        # 1. Fast path: already cached
        # -------------------------

        value = cache.get(self.key)

        if value is not None:
            return value

        # -------------------------
        # 2. Try to become the single
        #    cache filler (SET NX EX)
        # -------------------------

        lock = RedisLock(
            key=self.lock_key,
            timeout=self.lock_timeout,
        )

        if lock.acquire():
            try:
                # -------------------------
                # 3. Double-check: a previous filler may have
                #    finished between our miss and this lock
                # -------------------------

                value = cache.get(self.key)

                if value is not None:
                    return value

                # -------------------------
                # 4. Load from the source of truth
                # -------------------------

                value = loader()

                if value is None:
                    return None

                # -------------------------
                # 5. Publish for everyone else
                # -------------------------

                if self.set_loader_value:
                    cache.set(
                        self.key,
                        value,
                        timeout=self.timeout,
                    )

                return value

            finally:
                # Always release, even when the loader raised;
                # the lock TTL is the crash-safety net. Only the
                # token owner can release (atomic Lua check).
                lock.release()

        # -------------------------
        # 6. Another worker owns the fill: wait and re-read
        # -------------------------

        for _ in range(self.MAX_RETRIES):
            time.sleep(self.RETRY_DELAY)

            value = cache.get(self.key)

            if value is not None:
                return value

        # -------------------------
        # 7. Fail-open fallback: the fill did not land within the
        #    retry budget (slow or failed filler). Serve the
        #    request straight from the source instead of failing it.
        #    Exceptional path only; the normal flow stays
        #    single-flight.
        # -------------------------

        return loader()
