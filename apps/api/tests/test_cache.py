from django.core.cache import cache
from django.test import TestCase


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
