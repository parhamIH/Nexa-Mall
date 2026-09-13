import threading
import time

from django.core.cache import cache
from django.test import TestCase

from apps.api.cache import (
    AtomicCacheAside,
    StaleWhileRevalidateCache,
)
from apps.api.locks import RedisLock
from apps.api.redis import get_redis_client


class CacheInfrastructureTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_cache_set_and_get(self):
        cache.set(
            "nexa:test",
            {
                "status": "ok",
            },
            timeout=60,
        )

        value = cache.get(
            "nexa:test",
        )

        self.assertEqual(
            value,
            {
                "status": "ok",
            },
        )

    def test_cache_delete(self):
        cache.set(
            "nexa:test",
            "value",
            timeout=60,
        )

        cache.delete(
            "nexa:test",
        )

        self.assertIsNone(
            cache.get(
                "nexa:test",
            )
        )

    def test_cache_timeout(self):
        cache.set(
            "nexa:timeout",
            "value",
            timeout=1,
        )

        self.assertEqual(
            cache.get(
                "nexa:timeout",
            ),
            "value",
        )


class AtomicCacheAsideTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_cache_fill_uses_single_lock(self):
        loader_calls = []

        def loader():
            loader_calls.append(True)

            return {
                "value": "database",
            }

        cache_aside = AtomicCacheAside(
            key="nexa:test:atomic",
            lock_key="nexa:lock:test:atomic",
            timeout=300,
            lock_timeout=10,
        )

        first = cache_aside.get(
            loader=loader,
        )

        second = cache_aside.get(
            loader=loader,
        )

        self.assertEqual(
            first,
            {
                "value": "database",
            },
        )

        self.assertEqual(
            second,
            {
                "value": "database",
            },
        )

        self.assertEqual(
            len(loader_calls),
            1,
        )

    def test_only_one_request_can_acquire_lock(self):
        first = cache.add(
            "nexa:test:atomic-lock",
            "locked",
            timeout=10,
        )

        second = cache.add(
            "nexa:test:atomic-lock",
            "locked",
            timeout=10,
        )

        self.assertTrue(first)

        self.assertFalse(second)

    def test_loader_failure_releases_lock(self):
        client = get_redis_client()

        def failing_loader():
            raise ValueError(
                "Source exploded.",
            )

        cache_aside = AtomicCacheAside(
            key="nexa:test:fill-failure",
            lock_key="nexa:lock:test:fill-failure",
            timeout=300,
            lock_timeout=10,
        )

        with self.assertRaises(ValueError):
            cache_aside.get(
                loader=failing_loader,
            )

        # The lock is a raw token key outside Django's versioned
        # key space, so it must be checked with the raw client.
        self.assertIsNone(
            client.get(
                "nexa:lock:test:fill-failure",
            )
        )

        self.assertIsNone(
            cache.get(
                "nexa:test:fill-failure",
            )
        )


class CacheStampedeTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_only_one_loader_runs(self):
        loader_count = 0
        counter_lock = threading.Lock()

        def loader():
            nonlocal loader_count

            with counter_lock:
                loader_count += 1

            time.sleep(0.2)

            return {
                "value": "from-database",
            }

        cache_aside = AtomicCacheAside(
            key="nexa:test:stampede",
            lock_key="nexa:test:stampede:lock",
            timeout=300,
            lock_timeout=10,
        )

        results = []

        def worker():
            result = cache_aside.get(
                loader=loader,
            )

            results.append(result)

        threads = [
            threading.Thread(
                target=worker,
            )
            for _ in range(10)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(
            len(results),
            10,
        )

        self.assertTrue(
            all(
                result == {
                    "value": "from-database",
                }
                for result in results
            )
        )

        self.assertEqual(
            loader_count,
            1,
        )


class StaleWhileRevalidateCacheTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_fresh_value_is_returned_without_loader(self):
        key = "nexa:test:swr:fresh"
        lock_key = "nexa:test:swr:fresh:lock"

        cache.set(
            key,
            {
                "data": {
                    "value": "cached",
                },
                "stale_at": time.time() + 60,
            },
            timeout=300,
        )

        cache_aside = StaleWhileRevalidateCache(
            key=key,
            lock_key=lock_key,
            fresh_timeout=60,
            hard_timeout=300,
        )

        def loader():
            raise AssertionError(
                "Loader must not run for fresh data."
            )

        result = cache_aside.get(
            loader=loader,
        )

        self.assertEqual(
            result,
            {
                "value": "cached",
            },
        )

    def test_stale_value_can_be_returned(self):
        key = "nexa:test:swr:stale"
        lock_key = "nexa:test:swr:stale:lock"

        cache.set(
            key,
            {
                "data": {
                    "value": "old",
                },
                "stale_at": time.time() - 1,
            },
            timeout=300,
        )

        # Simulate another worker currently refreshing.
        other_worker = RedisLock(
            key=lock_key,
            timeout=10,
        )

        self.assertTrue(
            other_worker.acquire(),
        )

        try:
            cache_aside = StaleWhileRevalidateCache(
                key=key,
                lock_key=lock_key,
                fresh_timeout=60,
                hard_timeout=300,
            )

            result = cache_aside.get(
                loader=lambda: {
                    "value": "new",
                },
            )

            self.assertEqual(
                result,
                {
                    "value": "old",
                },
            )

        finally:
            other_worker.release()

    def test_stale_value_is_refreshed_by_lock_owner(self):
        key = "nexa:test:swr:refresh"
        lock_key = "nexa:test:swr:refresh:lock"

        cache.set(
            key,
            {
                "data": {
                    "value": "old",
                },
                "stale_at": time.time() - 1,
            },
            timeout=300,
        )

        cache_aside = StaleWhileRevalidateCache(
            key=key,
            lock_key=lock_key,
            fresh_timeout=60,
            hard_timeout=300,
        )

        result = cache_aside.get(
            loader=lambda: {
                "value": "new",
            },
        )

        self.assertEqual(
            result,
            {
                "value": "new",
            },
        )

        stored = cache.get(key)

        self.assertEqual(
            stored["data"],
            {
                "value": "new",
            },
        )

        self.assertGreater(
            stored["stale_at"],
            time.time(),
        )

    def test_hot_key_has_single_refresh(self):
        key = "nexa:test:swr:hot"
        lock_key = "nexa:test:swr:hot:lock"

        cache.set(
            key,
            {
                "data": {
                    "value": "old",
                },
                "stale_at": time.time() - 1,
            },
            timeout=300,
        )

        loader_calls = 0

        def loader():
            nonlocal loader_calls

            loader_calls += 1

            time.sleep(0.1)

            return {
                "value": "new",
            }

        cache_aside = StaleWhileRevalidateCache(
            key=key,
            lock_key=lock_key,
            fresh_timeout=60,
            hard_timeout=300,
        )

        result = cache_aside.get(
            loader=loader,
        )

        self.assertEqual(
            result,
            {
                "value": "new",
            },
        )

        self.assertEqual(
            loader_calls,
            1,
        )
