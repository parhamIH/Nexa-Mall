from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase

from apps.catalog.cache import (
    invalidate_product,
    invalidate_products,
    product_detail_key,
)
from apps.catalog.models import Product, ProductVariant
from apps.catalog.services.variant import VariantService
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

    # =========================================================
    # Variant → Product invalidation (invalidation graph)
    # =========================================================

    def test_variant_price_change_invalidates_product_cache(self):
        from rest_framework.test import APIClient

        client = APIClient()

        variant = VariantService.create_variant(
            product=self.product,
            sku="GRAPH-VARIANT-1",
            price=Decimal("500000"),
        )

        # Warm the product detail cache with the OLD price.
        first = client.get(
            f"/api/v1/catalog/products/"
            f"{self.product.id}/",
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        self.assertEqual(
            str(first.data["data"]["min_variant_price"]),
            "500000.00",
        )

        self.assertIsNotNone(
            cache.get(
                product_detail_key(
                    product_id=self.product.id,
                )
            )
        )

        # Variant price changes -> the PRODUCT representation is
        # stale. The invalidation runs on COMMIT; the next request
        # must rebuild from the database and see the NEW price.
        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            VariantService.update_variant(
                variant=variant,
                validated_data={
                    "price": Decimal("600000"),
                },
            )

        self.assertIsNone(
            cache.get(
                product_detail_key(
                    product_id=self.product.id,
                )
            )
        )

        second = client.get(
            f"/api/v1/catalog/products/"
            f"{self.product.id}/",
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertEqual(
            str(second.data["data"]["min_variant_price"]),
            "600000.00",
        )

    def test_variant_delete_invalidates_product_cache(self):
        variant = VariantService.create_variant(
            product=self.product_a,
            sku="GRAPH-VARIANT-DEL",
            price=Decimal("100000"),
        )

        cache.set(
            product_detail_key(
                product_id=self.product_a.id,
            ),
            {
                "id": str(self.product_a.id),
            },
            timeout=300,
        )

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            VariantService.delete_variant(
                variant=variant,
            )

        self.assertIsNone(
            cache.get(
                product_detail_key(
                    product_id=self.product_a.id,
                )
            )
        )

    def test_variant_create_invalidates_product_cache(self):
        cache.set(
            product_detail_key(
                product_id=self.product_b.id,
            ),
            {
                "id": str(self.product_b.id),
            },
            timeout=300,
        )

        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            VariantService.create_variant(
                product=self.product_b,
                sku="GRAPH-VARIANT-NEW",
                price=Decimal("100000"),
            )

        self.assertIsNone(
            cache.get(
                product_detail_key(
                    product_id=self.product_b.id,
                )
            )
        )
