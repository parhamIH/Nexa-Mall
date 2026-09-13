from django.core.cache import cache
from django.test import TestCase
from urllib.parse import parse_qs, urlparse

from apps.api.pagination import (
    StandardCursorPagination,
)
from apps.catalog.models import Product
from apps.tenants.models import Shop, Tenant


class CursorPaginationConfigTests(TestCase):

    def test_default_page_size(self):
        pagination = StandardCursorPagination()

        self.assertEqual(
            pagination.page_size,
            20,
        )

    def test_max_page_size(self):
        pagination = StandardCursorPagination()

        self.assertEqual(
            pagination.max_page_size,
            100,
        )

    def test_ordering_is_stable(self):
        pagination = StandardCursorPagination()

        self.assertEqual(
            pagination.ordering,
            "-created_at",
        )


class CursorPaginationAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Cursor Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Cursor Shop",
            slug="cursor-shop",
        )

        # Enough products for multiple 20-item pages.
        for i in range(45):
            Product.objects.create(
                shop=cls.shop,
                name=f"Cursor Product {i:03d}",
                slug=f"cursor-product-{i:03d}",
                status=Product.Status.ACTIVE,
            )

    def setUp(self):
        cache.clear()

    def test_product_list_uses_cursor_pagination(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "data",
            response.data,
        )

        self.assertIn(
            "meta",
            response.data,
        )

        self.assertIn(
            "next",
            response.data["meta"],
        )

        self.assertIn(
            "previous",
            response.data["meta"],
        )

        self.assertIn(
            "page_size",
            response.data["meta"],
        )

        # The cursor contract drops count/pages by design.
        self.assertNotIn(
            "count",
            response.data["meta"],
        )

        # First page is full but not everything.
        self.assertEqual(
            len(response.data["data"]),
            20,
        )

    def test_product_list_can_follow_cursor(self):
        first = self.client.get(
            "/api/v1/catalog/products/",
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        next_url = first.data["meta"]["next"]

        self.assertIsNotNone(
            next_url,
        )

        parsed = urlparse(next_url)

        cursor = parse_qs(parsed.query)["cursor"][0]

        second = self.client.get(
            "/api/v1/catalog/products/",
            {
                "cursor": cursor,
            },
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertIn(
            "data",
            second.data,
        )

        self.assertEqual(
            len(second.data["data"]),
            20,
        )

    def test_cursor_pages_do_not_repeat_products(self):
        first = self.client.get(
            "/api/v1/catalog/products/",
        )

        next_url = first.data["meta"]["next"]

        parsed = urlparse(next_url)

        cursor = parse_qs(parsed.query)["cursor"][0]

        second = self.client.get(
            "/api/v1/catalog/products/",
            {
                "cursor": cursor,
            },
        )

        first_ids = {
            item["id"]
            for item in first.data["data"]
        }

        second_ids = {
            item["id"]
            for item in second.data["data"]
        }

        self.assertTrue(
            first_ids.isdisjoint(
                second_ids,
            )
        )

        # All 45 products are covered by the two pages plus the tail.
        tail = self.client.get(
            "/api/v1/catalog/products/",
            {
                "cursor": parse_qs(
                    urlparse(
                        second.data["meta"]["next"]
                    ).query
                )["cursor"][0],
            },
        )

        tail_ids = {
            item["id"]
            for item in tail.data["data"]
        }

        self.assertEqual(
            len(first_ids | second_ids | tail_ids),
            45,
        )

    def test_public_list_rejects_arbitrary_ordering(self):
        # OrderingFilter is deliberately removed from the cursor
        # endpoint: the cursor is built on one fixed ordering.
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "ordering": "name",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        # The ordering parameter is ignored (unknown params neither
        # reorder the data nor mint new cache entries).
        names = [
            item["name"]
            for item in response.data["data"]
        ]

        self.assertNotEqual(
            names,
            sorted(names),
        )
