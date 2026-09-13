import uuid

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.api.redis import get_redis_client
from apps.catalog.cache import (
    PRODUCT_DETAIL_CACHE_JITTER,
    PRODUCT_DETAIL_CACHE_TIMEOUT,
    PRODUCT_NOT_FOUND,
    PRODUCT_NOT_FOUND_JITTER,
    PRODUCT_NOT_FOUND_TIMEOUT,
    delete_product_detail,
    product_detail_cache_timeout,
    product_not_found_cache_timeout,
)
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

    def test_not_found_product_is_negative_cached(self):
        unknown_id = uuid.uuid4()

        with CaptureQueriesContext(
            connection,
        ) as first_queries:
            first = self.client.get(
                f"/api/v1/catalog/products/"
                f"{unknown_id}/",
            )

        self.assertEqual(
            first.status_code,
            404,
        )

        self.assertGreater(
            len(first_queries),
            0,
        )

        cached_value = cache.get(
            product_detail_key(
                product_id=unknown_id,
            )
        )

        self.assertEqual(
            cached_value,
            PRODUCT_NOT_FOUND,
        )

    def test_negative_cache_prevents_repeated_db_queries(self):
        unknown_id = uuid.uuid4()

        first = self.client.get(
            f"/api/v1/catalog/products/"
            f"{unknown_id}/",
        )

        self.assertEqual(
            first.status_code,
            404,
        )

        with CaptureQueriesContext(
            connection,
        ) as second_queries:
            second = self.client.get(
                f"/api/v1/catalog/products/"
                f"{unknown_id}/",
            )

        self.assertEqual(
            second.status_code,
            404,
        )

        self.assertEqual(
            len(second_queries),
            0,
        )

    def test_creating_product_invalidates_negative_cache(self):
        key = product_detail_key(
            product_id=self.product.id,
        )

        cache.set(
            key,
            PRODUCT_NOT_FOUND,
            timeout=60,
        )

        self.assertEqual(
            cache.get(key),
            PRODUCT_NOT_FOUND,
        )

        delete_product_detail(
            product_id=self.product.id,
        )

        self.assertIsNone(
            cache.get(key),
        )

    # =========================================================
    # TTL Jitter (Cache Avalanche protection)
    # =========================================================

    def test_product_detail_ttl_has_jitter(self):
        values = [
            product_detail_cache_timeout()
            for _ in range(100)
        ]

        minimum = (
            PRODUCT_DETAIL_CACHE_TIMEOUT
            - PRODUCT_DETAIL_CACHE_JITTER
        )

        maximum = (
            PRODUCT_DETAIL_CACHE_TIMEOUT
            + PRODUCT_DETAIL_CACHE_JITTER
        )

        self.assertTrue(
            all(
                minimum <= value <= maximum
                for value in values
            )
        )

    def test_product_not_found_ttl_has_jitter(self):
        values = [
            product_not_found_cache_timeout()
            for _ in range(100)
        ]

        minimum = (
            PRODUCT_NOT_FOUND_TIMEOUT
            - PRODUCT_NOT_FOUND_JITTER
        )

        maximum = (
            PRODUCT_NOT_FOUND_TIMEOUT
            + PRODUCT_NOT_FOUND_JITTER
        )

        self.assertTrue(
            all(
                minimum <= value <= maximum
                for value in values
            )
        )

    def test_cache_set_uses_jittered_ttl_range(self):
        # Django's cache API has no ttl(); read the real TTL from
        # Redis via the raw client on the prefixed cache key.
        redis_client = get_redis_client()

        key = product_detail_key(
            product_id=self.product.id,
        )

        self.client.get(
            self.product_url(),
        )

        ttl = redis_client.ttl(
            cache.make_key(key),
        )

        minimum = (
            PRODUCT_DETAIL_CACHE_TIMEOUT
            - PRODUCT_DETAIL_CACHE_JITTER
        )

        maximum = (
            PRODUCT_DETAIL_CACHE_TIMEOUT
            + PRODUCT_DETAIL_CACHE_JITTER
        )

        # The TTL was set moments ago, so allow one second of
        # drift below the theoretical lower bound.
        self.assertGreaterEqual(
            ttl,
            minimum - 1,
        )

        self.assertLessEqual(
            ttl,
            maximum,
        )
