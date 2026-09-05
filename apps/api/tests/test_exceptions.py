from django.test import TestCase
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.test import APIRequestFactory

from apps.api.exceptions import custom_exception_handler


class ExceptionHandlerTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/test/")

    def test_validation_error_format(self):
        exc = ValidationError(
            {
                "quantity": [
                    "Must be greater than zero.",
                ],
            }
        )

        response = custom_exception_handler(
            exc,
            {
                "request": self.request,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["error"]["code"],
            "validation_error",
        )

        self.assertEqual(
            response.data["error"]["message"],
            "Validation failed.",
        )

        self.assertEqual(
            response.data["error"]["details"]["quantity"],
            [
                "Must be greater than zero.",
            ],
        )

    def test_not_found_format(self):
        exc = NotFound(
            "Product not found.",
        )

        response = custom_exception_handler(
            exc,
            {
                "request": self.request,
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            response.data["error"]["code"],
            "not_found",
        )

    def test_permission_denied_format(self):
        exc = PermissionDenied(
            "You cannot access this resource.",
        )

        response = custom_exception_handler(
            exc,
            {
                "request": self.request,
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.data["error"]["code"],
            "permission_denied",
        )

    def test_unhandled_exception_returns_none(self):
        exc = RuntimeError(
            "Unexpected error.",
        )

        response = custom_exception_handler(
            exc,
            {
                "request": self.request,
            },
        )

        self.assertIsNone(response)