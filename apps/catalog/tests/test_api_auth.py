from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class AuthenticationAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="user@example.com",
            password="test-password",
        )

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(
            "/api/v1/catalog/me/",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_authenticated_user_can_access_me(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {
                "email": "user@example.com",
                "password": "test-password",
            },
            format="json",
        )

        access_token = response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(
            "/api/v1/catalog/me/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["email"],
            "user@example.com",
        )