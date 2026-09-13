from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from urllib.parse import parse_qs, urlparse

from apps.catalog.models import (
    Product,
    ProductVariant,
)
from apps.tenants.models import Shop, Tenant


class ProductSearchRankingTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Search Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Search Shop",
            slug="search-shop",
        )

        cls.exact = Product.objects.create(
            shop=cls.shop,
            name="Nike Air Max",
            slug="nike-air-max",
            description="Running shoe",
            status=Product.Status.ACTIVE,
        )

        cls.partial = Product.objects.create(
            shop=cls.shop,
            name="Running Shoe",
            slug="running-shoe",
            description="Nike inspired running shoe",
            status=Product.Status.ACTIVE,
        )

        cls.other = Product.objects.create(
            shop=cls.shop,
            name="Adidas Runner",
            slug="adidas-runner",
            description="Sports shoe",
            status=Product.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.exact,
            sku="NIKE-AIR-001",
            name="Black",
            price=Decimal("1000000"),
            status=ProductVariant.Status.ACTIVE,
        )

    def setUp(self):
        cache.clear()

        self.client = APIClient()

    def test_search_results_are_ranked_by_relevance(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "nike",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        names = [
            item["name"]
            for item in response.data["data"]
        ]

        # Best trigram match first: the name hit outweighs the
        # description-only mention.
        self.assertEqual(
            names[0],
            "Nike Air Max",
        )

        self.assertIn(
            "Running Shoe",
            names,
        )

        self.assertNotIn(
            "Adidas Runner",
            names,
        )

    def test_variant_sku_can_boost_product_relevance(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "NIKE-AIR-001",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["data"][0]["name"],
            "Nike Air Max",
        )

    def test_ranked_search_follows_cursor(self):
        # Ranking must survive pagination: CursorPagination enforces
        # its own ordering, so the ranking only sticks if the
        # pagination adopts the relevance ordering.
        first = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "shoe",
                "page_size": "1",
            },
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        top_name = first.data["data"][0]["name"]

        next_url = first.data["meta"]["next"]

        self.assertIsNotNone(
            next_url,
        )

        cursor = parse_qs(
            urlparse(next_url).query
        )["cursor"][0]

        second = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "shoe",
                "page_size": "1",
                "cursor": cursor,
            },
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        second_name = second.data["data"][0]["name"]

        self.assertNotEqual(
            top_name,
            second_name,
        )

    def test_relevance_annotation_exists(self):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        from apps.catalog.api.filters.search import (
            TrigramProductSearchFilter,
        )

        factory = APIRequestFactory()

        request = Request(
            factory.get(
                "/api/v1/catalog/products/",
                {
                    "search": "nike",
                },
            )
        )

        queryset = Product.objects.filter(
            status=Product.Status.ACTIVE,
        )

        backend = TrigramProductSearchFilter()

        queryset = backend.filter_queryset(
            request,
            queryset,
            type(
                "View",
                (),
                {
                    "search_fields": [
                        "name",
                        "slug",
                        "description",
                        "brand__name",
                        "variants__sku",
                        "variants__name",
                    ],
                },
            ),
        )

        self.assertTrue(
            "search_relevance"
            in queryset.query.annotations,
        )

    def test_search_result_is_cached_after_ranking(self):
        first = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "nike",
            },
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        second = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "nike",
            },
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        # Cache serves the exact ranked representation.
        self.assertEqual(
            first.data,
            second.data,
        )
