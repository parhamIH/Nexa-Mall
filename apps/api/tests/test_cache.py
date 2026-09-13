import threading
import time

from django.core.cache import cache
from django.test import TestCase

from apps.api.cache import AtomicCacheAside
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
