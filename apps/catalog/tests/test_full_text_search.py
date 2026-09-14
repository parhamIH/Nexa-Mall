from decimal import Decimal

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.catalog.models import (
    Brand,
    Product,
    ProductVariant,
)
from apps.tenants.models import Shop, Tenant


class ProductFullTextSearchTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="FTS Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="FTS Shop",
            slug="fts-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Nike Running Shoes",
            slug="nike-running-shoes",
            description="Running footwear",
            status=Product.Status.ACTIVE,
        )

        cls.other_product = Product.objects.create(
            shop=cls.shop,
            name="Classic Running Shoes",
            slug="classic-running-shoes",
            description="Nike performance footwear",
            status=Product.Status.ACTIVE,
        )

        cls.unrelated = Product.objects.create(
            shop=cls.shop,
            name="Wool Sweater",
            slug="wool-sweater",
            description="Winter clothing",
            status=Product.Status.ACTIVE,
        )

    def setUp(self):
        cache.clear()

        self.client = APIClient()

    def test_full_text_search_finds_products(self):
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

        ids = {
            item["id"]
            for item in response.data["data"]
        }

        self.assertIn(
            str(self.product.id),
            ids,
        )

        self.assertIn(
            str(self.other_product.id),
            ids,
        )

        self.assertNotIn(
            str(self.unrelated.id),
            ids,
        )

    def test_product_name_has_higher_relevance(self):
        # A name hit (weight A) must outrank a description-only
        # mention (weight D) - that is the whole point of weighted
        # FTS ranking.
        query = SearchQuery(
            "nike",
            search_type="websearch",
            config="simple",
        )

        vector = (
            SearchVector(
                "name",
                weight="A",
                config="simple",
            )
            + SearchVector(
                "slug",
                weight="B",
                config="simple",
            )
            + SearchVector(
                "description",
                weight="D",
                config="simple",
            )
        )

        products = (
            Product.objects
            .filter(
                id__in=[
                    self.product.id,
                    self.other_product.id,
                ],
            )
            .annotate(
                rank=SearchRank(
                    vector,
                    query,
                ),
            )
            .order_by(
                "-rank",
            )
        )

        self.assertEqual(
            products.first().id,
            self.product.id,
        )

    def test_websearch_handles_multiple_terms(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "nike running",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = [
            item["id"]
            for item in response.data["data"]
        ]

        self.assertIn(
            str(self.product.id),
            ids,
        )

    def test_search_still_finds_brand_match(self):
        brand = Brand.objects.create(
            name="NikeOfficial",
            slug="nikeofficial",
        )

        branded = Product.objects.create(
            shop=self.shop,
            name="Performance Sneaker",
            slug="performance-sneaker",
            description="Everyday footwear",
            brand=brand,
            status=Product.Status.ACTIVE,
        )

        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "NikeOfficial",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data["data"]
        }

        # The brand fallback path is preserved: FTS does not know
        # about brand names, but the API contract still finds it.
        self.assertIn(
            str(branded.id),
            ids,
        )

    def test_search_still_finds_variant_sku_match(self):
        variant_product = Product.objects.create(
            shop=self.shop,
            name="Court Sneaker",
            slug="court-sneaker",
            description="Tennis footwear",
            status=Product.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=variant_product,
            sku="NIKE-COURT-42",
            name="White",
            price=Decimal("800000"),
            status=ProductVariant.Status.ACTIVE,
        )

        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "NIKE-COURT-42",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data["data"]
        }

        self.assertIn(
            str(variant_product.id),
            ids,
        )

    def test_ranked_ordering_survives_cursor_pagination(self):
        first = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "running",
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

        from urllib.parse import parse_qs, urlparse

        cursor = parse_qs(
            urlparse(next_url).query
        )["cursor"][0]

        second = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "running",
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

    def test_full_text_search_does_not_create_application_n_plus_one(self):
        with CaptureQueriesContext(
            connection,
        ) as queries:
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

        # Guard against accidental N+1 from the Exists subquery /
        # annotations. Not a final performance number - a regression
        # tripwire.
        self.assertLess(
            len(queries),
            10,
        )
