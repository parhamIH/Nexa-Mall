from decimal import Decimal

from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.catalog.api.filters.hybrid_search import (
    HybridProductSearchFilter,
)
from apps.catalog.models import (
    Brand,
    Product,
    ProductVariant,
)
from apps.tenants.models import Shop, Tenant


class SearchQueryCoverageTests(TestCase):
    """The search engine as a QUERY-TYPE MATRIX: one focused
    fixture, ten query types (exact / sku / brand / category /
    partial / multi-word / typo / no-result / short), each with its
    own expected behavior. A single shared data set keeps the
    matrix honest - the same rows the exact-name test sees are the
    rows the typo test must rescue and the no-result test must
    ignore.

    Fixture mirrors a real marketplace search corpus:
      - exact target:   "Nike Air Max 270" (brand + SKU)
      - same brand:     "Nike Running Shoes" (must follow exact)
      - different brand:"Adidas Running Shoes" (category-only hit)
      - same brand, non-product: "Nike Socks" (brand hit only)
      - category pool:  "Black Running Shoes" / "Black Sneakers"
    """

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Coverage Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Coverage Shop",
            slug="coverage-shop",
        )

        cls.nike = Brand.objects.create(
            name="Nike",
            slug="nike",
        )

        cls.adidas = Brand.objects.create(
            name="Adidas",
            slug="adidas",
        )

        cls.exact_product = Product.objects.create(
            shop=cls.shop,
            name="Nike Air Max 270",
            slug="nike-air-max-270",
            description="Running shoes with Air cushioning",
            brand=cls.nike,
            status=Product.Status.ACTIVE,
        )

        cls.running_product = Product.objects.create(
            shop=cls.shop,
            name="Nike Running Shoes",
            slug="nike-running-shoes",
            description="Running shoes for training",
            brand=cls.nike,
            status=Product.Status.ACTIVE,
        )

        cls.adidas_running_product = Product.objects.create(
            shop=cls.shop,
            name="Adidas Running Shoes",
            slug="adidas-running-shoes",
            description="Sports shoes",
            brand=cls.adidas,
            status=Product.Status.ACTIVE,
        )

        # Deliberately SIMILAR to the exact target: same brand,
        # same "air" token. This is the distractor the exact-match
        # ranking must beat - not a wildly different product, but
        # the nearest plausible competitor.
        cls.air_zoom_product = Product.objects.create(
            shop=cls.shop,
            name="Nike Air Zoom",
            slug="nike-air-zoom",
            description="Running shoes with Air cushioning",
            brand=cls.nike,
            status=Product.Status.ACTIVE,
        )

        # Same brand, NOT a shoe: only a brand-query hit, and a
        # ranking distractor for shoe queries.
        cls.nike_socks = Product.objects.create(
            shop=cls.shop,
            name="Nike Socks",
            slug="nike-socks",
            description="Sports socks",
            brand=cls.nike,
            status=Product.Status.ACTIVE,
        )

        cls.black_running_shoes = Product.objects.create(
            shop=cls.shop,
            name="Black Running Shoes",
            slug="black-running-shoes",
            description="Running shoes for training",
            status=Product.Status.ACTIVE,
        )

        cls.black_sneakers = Product.objects.create(
            shop=cls.shop,
            name="Black Sneakers",
            slug="black-sneakers",
            description="Casual footwear",
            status=Product.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.exact_product,
            sku="NIKE-AM-270",
            name="Black",
            price=Decimal("1000000"),
            status=ProductVariant.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.running_product,
            sku="NIKE-RUN-001",
            name="Black",
            price=Decimal("900000"),
            status=ProductVariant.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.adidas_running_product,
            sku="ADIDAS-RUN-001",
            name="Black",
            price=Decimal("800000"),
            status=ProductVariant.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.air_zoom_product,
            sku="NK-AZ-90",
            name="White",
            price=Decimal("950000"),
            status=ProductVariant.Status.ACTIVE,
        )

    def search(self, query: str):
        factory = APIRequestFactory()

        django_request = factory.get(
            "/api/v1/products/",
            {"search": query},
        )

        request = Request(django_request)

        queryset = Product.objects.filter(
            shop=self.shop,
            status=Product.Status.ACTIVE,
        )

        return HybridProductSearchFilter().filter_queryset(
            request,
            queryset,
            view=None,
        )

    def result_slugs(self, query: str) -> list[str]:
        return list(
            self.search(query).values_list(
                "slug",
                flat=True,
            )
        )

    def assert_all_in(self, query: str, slugs: list[str]):
        result = self.result_slugs(query)

        for slug in slugs:
            self.assertIn(
                slug,
                result,
                f"{slug!r} missing from results for {query!r}",
            )

    def assert_first(self, query: str, slug: str):
        result = self.result_slugs(query)

        self.assertTrue(
            result,
            f"no results for {query!r}",
        )

        self.assertEqual(
            result[0],
            slug,
            f"expected {slug!r} first for {query!r}, got {result}",
        )

    def test_exact_product_name_ranks_first(self):
        # Exact product: the product the query names must be #1.
        self.assert_first("nike air max", "nike-air-max-270")

    def test_sku_exact_match(self):
        # SKU is the strongest variant-level signal: exact SKU hit
        # beats every name/brand signal.
        self.assert_first("NIKE-AM-270", "nike-air-max-270")

    def test_sku_variant_icontains(self):
        # Partial SKU (case-insensitive substring) still resolves.
        self.assertIn(
            "nike-air-max-270",
            self.result_slugs("am-270"),
        )

    def test_brand_query_returns_all_brand_products(self):
        # Brand-only query: every brand product is relevant, the
        # non-brand product is not.
        self.assert_all_in(
            "nike",
            [
                "nike-air-max-270",
                "nike-running-shoes",
                "nike-socks",
            ],
        )

    def test_category_query_across_brands(self):
        # Category-ish query spans brands: both running-shoe brands
        # are relevant.
        self.assert_all_in(
            "running shoes",
            [
                "nike-running-shoes",
                "adidas-running-shoes",
            ],
        )

    def test_partial_query_finds_substring(self):
        # Partial name / substring: the target URL fragment still
        # resolves through the trigram/icontains channel.
        self.assertIn(
            "nike-air-max-270",
            self.result_slugs("air max 270"),
        )

    def test_multi_word_query(self):
        self.assert_all_in(
            "nike running",
            [
                "nike-running-shoes",
            ],
        )

    def test_typo_query_rescued_by_trigram(self):
        # Deliberate typo: FTS kills the whole token path, only the
        # trigram candidate branch can rescue it.
        self.assertIn(
            "nike-air-max-270",
            self.result_slugs("nkie air max"),
        )

    def test_short_query_finds_products(self):
        # Very short query (2 chars): must not error, must find the
        # product whose name starts with them.
        self.assertIn(
            "nike-air-max-270",
            self.result_slugs("ai"),
        )

    def test_no_result_query_returns_empty(self):
        # Out-of-catalog query: no noise, no crash, empty list.
        self.assertEqual(
            self.result_slugs("xyzabc123"),
            [],
        )

    def test_rank_exact_beats_similar(self):
        # Exact name match must outrank the nearest plausible
        # competitor: same brand AND the shared "air" token.
        result = self.result_slugs("nike air max")

        self.assertLess(
            result.index("nike-air-max-270"),
            result.index("nike-air-zoom"),
        )

    def test_rank_exact_sku_beats_brand_grazes(self):
        # SKU query: the SKU holder must beat brand-only grazes.
        # nike-socks / nike-air-zoom share the brand but not the
        # SKU token - they may not even be retrieved for this
        # query; the contract is that the SKU holder is FIRST.
        result = self.result_slugs("NIKE-AM-270")

        self.assertTrue(result)

        self.assertEqual(
            result[0],
            "nike-air-max-270",
        )