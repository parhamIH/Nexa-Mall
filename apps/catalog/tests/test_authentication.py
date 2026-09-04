from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class AuthenticationTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="auth@example.com",
            password="test-password",
        )

    def test_obtain_access_token(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {
                "email": "auth@example.com",
                "password": "test-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "access",
            response.data,
        )

        self.assertIn(
            "refresh",
            response.data,
        )

    def test_invalid_credentials_are_rejected(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {
                "email": "auth@example.com",
                "password": "wrong-password",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )