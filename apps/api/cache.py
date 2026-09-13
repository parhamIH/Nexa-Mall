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
        timeout: int | Callable[[], int],
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

    def _get_timeout(self) -> int:
        # Static ints are used as-is; callables are evaluated at
        # fill time so a jittered TTL is decided per fill and never
        # re-rolled on a cache hit.
        if callable(self.timeout):
            return self.timeout()

        return self.timeout

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
                        timeout=self._get_timeout(),
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


class StaleWhileRevalidateCache:
    """
    Stale-while-revalidate cache for hot keys (breakdown protection).

    Each entry carries two lifetimes:
    - fresh (until stale_at): served immediately, no source access
    - hard (the Redis TTL): after stale_at the previous value is
      still served instantly while exactly one worker refreshes;
      only past the hard TTL does the key really disappear

    On a hot key this keeps latency flat: 10,000 concurrent requests
    on a stale entry -> one worker reloads from the source, everyone
    else gets the previous value immediately instead of queueing
    behind the lock (plain single-flight would serialize them).

    Suitable only for domains where a slightly old value is
    business-acceptable (catalog content); never for
    consistency-sensitive state (inventory, payments, order status).

    set_loader_value=False: the loader publishes its own outcome
    with domain-specific TTLs (e.g. a fresh/hard envelope or a raw
    negative marker); this helper then only coordinates the
    fresh/stale/lock flow.
    """

    RETRY_DELAY = 0.05
    MAX_RETRIES = 100

    def __init__(
        self,
        *,
        key: str,
        lock_key: str,
        fresh_timeout: int,
        hard_timeout: int,
        lock_timeout: int = 10,
        set_loader_value: bool = True,
    ):
        if fresh_timeout <= 0:
            raise ValueError(
                "fresh_timeout must be greater than zero."
            )

        if hard_timeout <= fresh_timeout:
            raise ValueError(
                "hard_timeout must be greater than "
                "fresh_timeout."
            )

        self.key = key
        self.lock_key = lock_key
        self.fresh_timeout = fresh_timeout
        self.hard_timeout = hard_timeout
        self.lock_timeout = lock_timeout
        self.set_loader_value = set_loader_value

    def _build_envelope(
        self,
        data: Any,
    ) -> dict:
        return {
            "data": data,
            "stale_at": time.time()
            + self.fresh_timeout,
        }

    def _get_envelope(self):
        return cache.get(self.key)

    def _is_envelope(
        self,
        value,
    ) -> bool:
        return (
            isinstance(value, dict)
            and "data" in value
            and "stale_at" in value
        )

    def _is_stale(
        self,
        envelope: dict,
    ) -> bool:
        return time.time() >= envelope["stale_at"]

    def _set(
        self,
        data,
    ):
        cache.set(
            self.key,
            self._build_envelope(data),
            timeout=self.hard_timeout,
        )

    def get(
        self,
        loader: Callable[[], Any],
    ):
        # --------------------------------
        # 1. Fast path
        # --------------------------------

        cached = self._get_envelope()

        if cached is not None:
            # Raw (non-envelope) values are legacy entries or
            # negative markers: serve them as-is; their own TTL
            # governs them.
            if not self._is_envelope(cached):
                return cached

            if not self._is_stale(cached):
                return cached["data"]

        # --------------------------------
        # 2. Cache is stale or missing
        # --------------------------------

        stale_data = None

        if self._is_envelope(cached):
            stale_data = cached["data"]

        lock = RedisLock(
            key=self.lock_key,
            timeout=self.lock_timeout,
        )

        # --------------------------------
        # 3. Try to become the revalidator
        # --------------------------------

        if lock.acquire():
            try:
                # ----------------------------
                # Double check
                # ----------------------------

                cached = self._get_envelope()

                if (
                    self._is_envelope(cached)
                    and not self._is_stale(cached)
                ):
                    return cached["data"]

                # ----------------------------
                # Refresh from the source
                # ----------------------------

                data = loader()

                if data is None:
                    return None

                if self.set_loader_value:
                    self._set(data)

                return data

            finally:
                lock.release()

        # --------------------------------
        # 4. Another worker is refreshing
        # --------------------------------

        if stale_data is not None:
            # Serve the previous value immediately instead of
            # queueing behind the lock (hot-key behavior).
            return stale_data

        # --------------------------------
        # 5. No stale value exists:
        #    single-flight wait for the fill
        # --------------------------------

        for _ in range(
            self.MAX_RETRIES,
        ):
            time.sleep(
                self.RETRY_DELAY,
            )

            cached = self._get_envelope()

            if cached is None:
                continue

            if not self._is_envelope(cached):
                return cached

            if not self._is_stale(cached):
                return cached["data"]

        # --------------------------------
        # 6. Fail-open fallback
        # --------------------------------

        return loader()
