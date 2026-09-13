import time
from collections.abc import Callable
from typing import Any

from django.core.cache import cache


class AtomicCacheAside:
    """
    Cache-aside with single-flight (stampede) protection.

    GET / SET / ADD are each a single atomic Redis command, but the
    GET -> source -> SET chain is not atomic: without coordination,
    N concurrent misses would all hit the source at once. This helper
    uses a lock (cache.add has add-if-not-exists semantics) so that
    per key only one worker performs the expensive fill while the
    others wait and re-read.

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
    ):
        self.key = key
        self.lock_key = lock_key
        self.timeout = timeout
        self.lock_timeout = lock_timeout

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
        # 2. Try to become the single cache filler
        # -------------------------

        acquired = cache.add(
            self.lock_key,
            "locked",
            timeout=self.lock_timeout,
        )

        if acquired:
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

                cache.set(
                    self.key,
                    value,
                    timeout=self.timeout,
                )

                return value

            finally:
                # Always release, even when the loader raised;
                # the lock TTL is the crash-safety net.
                cache.delete(self.lock_key)

        # -------------------------
        # 6. Another worker owns the fill: wait and re-read
        # -------------------------

        for _ in range(self.MAX_RETRIES):
            time.sleep(self.RETRY_DELAY)

            value = cache.get(self.key)

            if value is not None:
                return value

            # The filler finished (or its lock expired) without
            # publishing a value - typically a loader that raised,
            # e.g. a 404. Stop waiting and go to the source instead
            # of burning the full retry budget: a contended 404 must
            # not turn every waiter into a 5-second request.
            if cache.get(self.lock_key) is None:
                break

        # Fallback: fill it ourselves
        # (availability over stampede protection).
        return loader()
