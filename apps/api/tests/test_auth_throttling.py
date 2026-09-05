from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.api.throttling import AuthRateThrottle


User = get_user_model()


class AuthThrottleTests(TestCase):
    """
    Login endpoints are wrapped with AuthRateThrottle (IP based).
    DRF snapshots throttle rates at import time, so the test sets the
    rate directly on the throttle class instead of override_settings.
    The cache is also cleared on cleanup so later login tests are not
    polluted with this class's throttle history.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

        self.client = APIClient()

        User.objects.create_user(
            email="login-throttle@example.com",
            password="test-password",
        )

        AuthRateThrottle.rate = "2/min"
        self.addCleanup(
            setattr,
            AuthRateThrottle,
            "rate",
            None,
        )

    def test_login_is_throttled(self):
        url = "/api/v1/auth/token/"

        data = {
            "email": "login-throttle@example.com",
            "password": "test-password",
        }

        first = self.client.post(
            url,
            data,
            format="json",
        )

        second = self.client.post(
            url,
            data,
            format="json",
        )

        third = self.client.post(
            url,
            data,
            format="json",
        )

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