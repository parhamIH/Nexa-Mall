from django.test import TestCase
from rest_framework.test import APIClient


class SchemaTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_schema_endpoint_is_available(self):
        response = self.client.get(
            "/api/schema/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "openapi",
            response.data,
        )

    def test_swagger_ui_is_available(self):
        response = self.client.get(
            "/api/docs/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_redoc_is_available(self):
        response = self.client.get(
            "/api/redoc/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )