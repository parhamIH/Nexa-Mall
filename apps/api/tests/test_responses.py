from django.test import TestCase

from apps.api.responses import success_response


class ResponseContractTests(TestCase):

    def test_success_response_has_standard_structure(self):
        response = success_response(
            data={
                "id": "123",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["data"],
            {
                "id": "123",
            },
        )

        self.assertEqual(
            response.data["meta"],
            {},
        )

    def test_success_response_accepts_meta(self):
        response = success_response(
            data=[
                {
                    "id": "123",
                }
            ],
            meta={
                "count": 1,
            },
        )

        self.assertEqual(
            response.data["data"],
            [
                {
                    "id": "123",
                }
            ],
        )

        self.assertEqual(
            response.data["meta"]["count"],
            1,
        )

    def test_success_response_status(self):
        response = success_response(
            data={
                "created": True,
            },
            status_code=201,
        )

        self.assertEqual(
            response.status_code,
            201,
        )