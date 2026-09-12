from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

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
                f"product:{self.product.id}"
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
                f"product:{self.product.id}"
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
                f"product:{self.product.id}"
            )
        )
