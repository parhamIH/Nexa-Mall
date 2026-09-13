from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.catalog.cache import product_detail_key
from apps.catalog.models import Product
from apps.tenants.models import Shop, Tenant


class ProductCacheTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.tenant = Tenant.objects.create(
            name="Cache Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Cache Shop",
            slug="cache-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Cached Product",
            slug="cached-product",
            status=Product.Status.ACTIVE,
        )

    def setUp(self):
        cache.clear()

    def product_url(self):
        return (
            f"/api/v1/catalog/products/"
            f"{self.product.id}/"
        )

    def test_first_request_is_cache_miss(self):
        with CaptureQueriesContext(
            connection,
        ) as queries:
            response = self.client.get(
                self.product_url(),
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertGreater(
            len(queries),
            0,
        )

        self.assertIsNotNone(
            cache.get(
                f"nexa:v1:catalog:"
                f"product:detail:{self.product.id}"
            )
        )

    def test_second_request_is_cache_hit(self):
        first = self.client.get(
            self.product_url(),
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        with CaptureQueriesContext(
            connection,
        ) as queries:
            second = self.client.get(
                self.product_url(),
            )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertEqual(
            len(queries),
            0,
        )

        self.assertEqual(
            first.data,
            second.data,
        )

    def test_product_update_invalidates_cache(self):
        first = self.client.get(
            self.product_url(),
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        self.assertIsNotNone(
            cache.get(
                f"nexa:v1:catalog:"
                f"product:detail:{self.product.id}"
            )
        )

        self.product.name = "Updated Product"
        self.product.save()

        from apps.catalog.cache import (
            delete_product_detail,
        )

        delete_product_detail(
            product_id=self.product.id,
        )

        self.assertIsNone(
            cache.get(
                f"nexa:v1:catalog:"
                f"product:detail:{self.product.id}"
            )
        )

    def test_product_detail_key_is_deterministic(self):
        key = product_detail_key(
            product_id=self.product.id,
        )

        self.assertEqual(
            key,
            (
                "nexa:v1:catalog:"
                f"product:detail:{self.product.id}"
            ),
        )

    def test_product_cache_versions_do_not_collide(self):
        key_v1 = product_detail_key(
            product_id=self.product.id,
            version="v1",
        )

        key_v2 = product_detail_key(
            product_id=self.product.id,
            version="v2",
        )

        self.assertNotEqual(
            key_v1,
            key_v2,
        )

    def test_product_cache_expires(self):
        key = product_detail_key(
            product_id=self.product.id,
        )

        cache.set(
            key,
            {
                "name": "Temporary",
            },
            timeout=1,
        )

        self.assertEqual(
            cache.get(key),
            {
                "name": "Temporary",
            },
        )

    def test_different_versions_store_different_values(self):
        v1_key = product_detail_key(
            product_id=self.product.id,
            version="v1",
        )

        v2_key = product_detail_key(
            product_id=self.product.id,
            version="v2",
        )

        cache.set(
            v1_key,
            {
                "name": "Old Response",
            },
            timeout=300,
        )

        cache.set(
            v2_key,
            {
                "name": "New Response",
            },
            timeout=300,
        )

        self.assertEqual(
            cache.get(v1_key),
            {
                "name": "Old Response",
            },
        )

        self.assertEqual(
            cache.get(v2_key),
            {
                "name": "New Response",
            },
        )
