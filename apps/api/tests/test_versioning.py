from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class VersioningTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # The public list endpoint is cached by query combination
        # (no product ids in the key); clear it so this test class
        # never serves a stale entry left over from another test.
        cache.clear()

    def test_v1_catalog_endpoint_is_available(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_unsupported_version_is_rejected(self):
        response = self.client.get(
            "/api/v2/catalog/products/",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_request_contains_api_version(self):
        user = User.objects.create_user(
            email="version@example.com",
            password="test-password",
        )

        self.client.force_authenticate(
            user=user,
        )

        response = self.client.get(
            "/api/v1/catalog/me/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["data"]["version"],
            "v1",
        )