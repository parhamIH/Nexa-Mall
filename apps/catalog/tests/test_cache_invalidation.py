from django.core.cache import cache
from django.test import TestCase

from apps.catalog.cache import (
    invalidate_product,
    invalidate_products,
    product_detail_key,
)
from apps.catalog.models import Product
from apps.tenants.models import Shop, Tenant


class ProductCacheInvalidationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Invalidation Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Invalidation Shop",
            slug="invalidation-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Invalidation Product",
            slug="invalidation-product",
            status=Product.Status.ACTIVE,
        )

        cls.product_a = Product.objects.create(
            shop=cls.shop,
            name="Product A",
            slug="product-a",
            status=Product.Status.ACTIVE,
        )

        cls.product_b = Product.objects.create(
            shop=cls.shop,
            name="Product B",
            slug="product-b",
            status=Product.Status.ACTIVE,
        )

    def setUp(self):
        cache.clear()

    def test_product_invalidation_runs_after_commit(self):
        key = product_detail_key(
            product_id=self.product.id,
        )

        cache.set(
            key,
            {
                "name": "Cached Product",
            },
            timeout=300,
        )

        with self.captureOnCommitCallbacks(
            execute=True,
        ) as callbacks:
            invalidate_product(
                product_id=self.product.id,
            )

        # Exactly one invalidation was scheduled and it ran.
        self.assertEqual(
            len(callbacks),
            1,
        )

        self.assertIsNone(
            cache.get(key),
        )

    def test_multiple_products_can_be_invalidated(self):
        product_ids = [
            self.product_a.id,
            self.product_b.id,
        ]

        for product_id in product_ids:
            cache.set(
                product_detail_key(
                    product_id=product_id,
                ),
                {
                    "id": str(product_id),
                },
                timeout=300,
            )

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            invalidate_products(
                product_ids=product_ids,
            )

        for product_id in product_ids:
            self.assertIsNone(
                cache.get(
                    product_detail_key(
                        product_id=product_id,
                    )
                )
            )

    def test_rollback_keeps_cache_intact(self):
        key = product_detail_key(
            product_id=self.product.id,
        )

        cache.set(
            key,
            {
                "name": "Cached Product",
            },
            timeout=300,
        )

        def failing_operation():
            invalidate_product(
                product_id=self.product.id,
            )

            raise ValueError(
                "Simulated failure inside the transaction."
            )

        # The invalidation is registered on COMMIT; because the
        # transaction never commits (exception raised inside
        # transaction.atomic), the cache delete must NOT run and
        # the cache entry stays intact.
        from django.db import transaction

        with self.assertRaises(ValueError):
            with transaction.atomic():
                failing_operation()

        self.assertIsNotNone(
            cache.get(key),
        )
