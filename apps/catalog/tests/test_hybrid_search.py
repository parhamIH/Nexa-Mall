from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from urllib.parse import parse_qs, urlparse

from apps.catalog.models import (
    Brand,
    Product,
    ProductVariant,
)
from apps.tenants.models import Shop, Tenant


class HybridSearchTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Hybrid Search Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Hybrid Search Shop",
            slug="hybrid-search-shop",
        )

        cls.brand = Brand.objects.create(
            name="Nike",
            slug="nike",
        )

        cls.exact_product = Product.objects.create(
            shop=cls.shop,
            name="Nike Air",
            slug="nike-air",
            description="Running shoes",
            brand=cls.brand,
            status=Product.Status.ACTIVE,
        )

        cls.description_product = Product.objects.create(
            shop=cls.shop,
            name="Running Shoes",
            slug="running-shoes",
            description="Inspired by Nike Air",
            status=Product.Status.ACTIVE,
        )

        cls.other_product = Product.objects.create(
            shop=cls.shop,
            name="Adidas Runner",
            slug="adidas-runner",
            description="Sports footwear",
            status=Product.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.exact_product,
            sku="NIKE-AIR-001",
            name="Black",
            price=Decimal("1000000"),
            status=ProductVariant.Status.ACTIVE,
        )

    def setUp(self):
        cache.clear()

        self.client = APIClient()

    def test_exact_name_match_is_ranked_first(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "Nike Air",
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

        self.assertEqual(
            names[0],
            "Nike Air",
        )

    def test_search_does_not_return_unrelated_product(
        self,
    ):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "Nike",
            },
        )

        names = [
            item["name"]
            for item in response.data["data"]
        ]

        self.assertNotIn(
            "Adidas Runner",
            names,
        )

    def test_brand_match_is_searchable(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "Nike",
            },
        )

        names = [
            item["name"]
            for item in response.data["data"]
        ]

        self.assertIn(
            "Nike Air",
            names,
        )

    def test_variant_sku_is_searchable(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "NIKE-AIR-001",
            },
        )

        names = [
            item["name"]
            for item in response.data["data"]
        ]

        self.assertIn(
            "Nike Air",
            names,
        )


    def test_hybrid_filter_creates_relevance_score(
        self,
    ):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        from apps.catalog.api.filters.hybrid_search import (
            HybridProductSearchFilter,
        )

        factory = APIRequestFactory()

        request = Request(
            factory.get(
                "/api/v1/catalog/products/",
                {
                    "search": "Nike",
                },
            )
        )

        queryset = Product.objects.filter(
            status=Product.Status.ACTIVE,
        )

        backend = HybridProductSearchFilter()

        filtered = backend.filter_queryset(
            request,
            queryset,
            None,
        )

        self.assertIn(
            "search_score",
            filtered.query.annotations,
        )

    def test_hybrid_ranked_ordering_survives_cursor_pagination(
        self,
    ):
        # Same class of bug as ADR-003 (float4 cursor positions):
        # the scaled-integer score must produce disjoint pages.
        first = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "nike",
                "page_size": "1",
            },
        )

        self.assertEqual(
            first.status_code,
            200,
        )

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
                "search": "nike",
                "page_size": "1",
                "cursor": cursor,
            },
        )

        self.assertEqual(
            second.status_code,
            200,
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
            first_ids.isdisjoint(second_ids),
        )

    def test_hybrid_search_does_not_create_application_n_plus_one(
        self,
    ):
        from django.db import connection
        from django.test.utils import (
            CaptureQueriesContext,
        )

        with CaptureQueriesContext(
            connection,
        ) as queries:
            response = self.client.get(
                "/api/v1/catalog/products/",
                {
                    "search": "Nike",
                },
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        # Guard against accidental N+1. Not a benchmark.
        self.assertLess(
            len(queries),
            10,
        )
