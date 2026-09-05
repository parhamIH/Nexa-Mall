from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import (
    AnonRateThrottle,
    UserRateThrottle,
)


User = get_user_model()


class AnonymousThrottleTests(TestCase):
    """
    DRF snapshots DEFAULT_THROTTLE_RATES / DEFAULT_THROTTLE_CLASSES as
    class attributes at import time, so @override_settings cannot change
    them in tests. The reliable lever is setting `rate` directly on the
    throttle class (same approach DRF's own test suite uses).
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        AnonRateThrottle.rate = "2/min"
        self.addCleanup(
            setattr,
            AnonRateThrottle,
            "rate",
            None,
        )

    def test_anon_throttle_can_block_requests(self):
        # Use an existing public endpoint.
        url = "/api/v1/catalog/products/"

        first = self.client.get(url)
        second = self.client.get(url)
        third = self.client.get(url)

        self.assertIn(
            first.status_code,
            [200, 404],
        )

        self.assertIn(
            second.status_code,
            [200, 404],
        )

        self.assertEqual(
            third.status_code,
            429,
        )


class UserThrottleTests(TestCase):

    def setUp(self):
        cache.clear()

        self.client = APIClient()

        self.user = User.objects.create_user(
            email="throttle@example.com",
            password="test-password",
        )

        self.client.force_authenticate(
            user=self.user,
        )

        UserRateThrottle.rate = "2/min"
        self.addCleanup(
            setattr,
            UserRateThrottle,
            "rate",
            None,
        )

    def test_user_throttle_can_block_requests(self):
        url = "/api/v1/catalog/me/"

        first = self.client.get(url)
        second = self.client.get(url)
        third = self.client.get(url)

        self.assertEqual(
            first.status_code,
            200,
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertEqual(
            third.status_code,
            429,
        )