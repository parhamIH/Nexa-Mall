from django.core.cache import cache
from django.test import TestCase

from apps.api.locks import RedisLock


class RedisLockTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_only_owner_can_release_lock(self):
        owner = RedisLock(
            key="nexa:test:ownership",
            timeout=10,
        )

        attacker = RedisLock(
            key="nexa:test:ownership",
            timeout=10,
        )

        self.assertTrue(
            owner.acquire(),
        )

        self.assertFalse(
            attacker.acquire(),
        )

        self.assertFalse(
            attacker.release(),
        )

        self.assertTrue(
            owner.release(),
        )

    def test_lock_can_be_reacquired_after_release(self):
        first = RedisLock(
            key="nexa:test:reacquire",
            timeout=10,
        )

        second = RedisLock(
            key="nexa:test:reacquire",
            timeout=10,
        )

        self.assertTrue(
            first.acquire(),
        )

        self.assertTrue(
            first.release(),
        )

        self.assertTrue(
            second.acquire(),
        )

        self.assertTrue(
            second.release(),
        )
