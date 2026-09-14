from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase

from apps.catalog.models import (
    Brand,
    Product,
    ProductVariant,
)
from apps.catalog.search.adapter import HybridSearchAdapter
from apps.catalog.search.benchmark import run_search_benchmark
from apps.tenants.models import Shop, Tenant


class HybridSearchAdapterIntegrationTests(TestCase):
    """Integration: the REAL filter, the REAL database, the REAL
    ranking the API serves - no mocks. The adapter only translates
    the ranked queryset to slugs for the benchmark layer."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Adapter Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Adapter Shop",
            slug="adapter-shop",
        )

        cls.brand = Brand.objects.create(
            name="Nike",
            slug="nike",
        )

        cls.nike_air_max = Product.objects.create(
            shop=cls.shop,
            name="Nike Air Max",
            slug="nike-air-max",
            description="Running shoes",
            brand=cls.brand,
            status=Product.Status.ACTIVE,
        )

        cls.nike_running = Product.objects.create(
            shop=cls.shop,
            name="Nike Running",
            slug="nike-running",
            description="Running shoes",
            brand=cls.brand,
            status=Product.Status.ACTIVE,
        )

        cls.nike_shirt = Product.objects.create(
            shop=cls.shop,
            name="Nike Shirt",
            slug="nike-shirt",
            description="Sports apparel",
            brand=cls.brand,
            status=Product.Status.ACTIVE,
        )

        cls.black_running_shoes = Product.objects.create(
            shop=cls.shop,
            name="Black Running Shoes",
            slug="black-running-shoes",
            description="Running shoes",
            status=Product.Status.ACTIVE,
        )

        cls.black_sneakers = Product.objects.create(
            shop=cls.shop,
            name="Black Sneakers",
            slug="black-sneakers",
            description="Casual footwear",
            status=Product.Status.ACTIVE,
        )

        cls.adidas_shoe = Product.objects.create(
            shop=cls.shop,
            name="Adidas Shoe",
            slug="adidas-shoe",
            description="Sports footwear",
            status=Product.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=cls.nike_air_max,
            sku="NIKE-AIR-MAX-001",
            name="Black",
            price=Decimal("1000000"),
            status=ProductVariant.Status.ACTIVE,
        )

    def setUp(self):
        cache.clear()

        self.adapter = HybridSearchAdapter()

    def test_exact_product_name_ranks_first(self):
        result = self.adapter.search("nike air max")

        self.assertEqual(
            result[0],
            "nike-air-max",
        )

    def test_sku_search_ranks_correct_product_first(self):
        result = self.adapter.search("NIKE-AIR-MAX-001")

        self.assertEqual(
            result[0],
            "nike-air-max",
        )

    def test_typo_still_finds_product(self):
        # Trigram similarity must absorb a simple typo that
        # token-based FTS alone would miss.
        result = self.adapter.search("nike air mx")

        self.assertIn(
            "nike-air-max",
            result[:5],
        )

    def test_unrelated_products_are_not_retrieved(self):
        result = self.adapter.search("nike")

        self.assertNotIn(
            "adidas-shoe",
            result,
        )

    def test_scoped_base_queryset_limits_search(self):
        # Multi-tenant contract: the adapter must honor a scoped
        # base queryset (isolation BEFORE ranking, never after).
        scoped = HybridSearchAdapter(
            base_queryset=lambda: Product.objects.filter(
                id=self.black_sneakers.id,
            )
        )

        result = scoped.search("nike")

        self.assertNotIn(
            "nike-air-max",
            result,
        )

    def test_hybrid_search_benchmark(self):
        # The real baseline against the real ranking. Asserted
        # bounds are deliberately soft: they guard against gross
        # regressions (e.g. ranking silently dropped by pagination
        # or a filter rewrite), NOT a quality target - tuning the
        # weights against a real validated baseline comes next,
        # and hard-locking numbers now would invite tuning the
        # data to the test.
        result = run_search_benchmark(
            self.adapter.search,
        )

        self.assertGreater(
            result.mrr,
            0.5,
            f"baseline regressed: {result}",
        )

        self.assertGreater(
            result.precision_at_5,
            0.5,
            f"baseline regressed: {result}",
        )

        self.assertGreater(
            result.recall_at_5,
            0.5,
            f"baseline regressed: {result}",
        )
