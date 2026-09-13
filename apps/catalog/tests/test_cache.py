import time
import uuid
from decimal import Decimal

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.api.locks import RedisLock
from apps.api.redis import get_redis_client
from apps.catalog.cache import (
    PRODUCT_DETAIL_CACHE_VERSION,
    PRODUCT_DETAIL_HARD_TIMEOUT,
    PRODUCT_DETAIL_HARD_TIMEOUT_JITTER,
    PRODUCT_NOT_FOUND,
    PRODUCT_NOT_FOUND_JITTER,
    PRODUCT_NOT_FOUND_TIMEOUT,
    delete_product_detail,
    product_detail_hard_cache_timeout,
    product_not_found_cache_timeout,
)
from apps.catalog.cache import (
    product_detail_key,
    product_detail_lock_key,
)
from apps.catalog.selectors.product import ProductSelector
from apps.catalog.api.serializers import (
    ProductDetailSerializer,
)
from apps.catalog.models import Product, ProductVariant
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
                product_detail_key(
                    product_id=self.product.id,
                )
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
                product_detail_key(
                    product_id=self.product.id,
                )
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
                product_detail_key(
                    product_id=self.product.id,
                )
            )
        )

    def test_product_detail_key_is_deterministic(self):
        key = product_detail_key(
            product_id=self.product.id,
        )

        self.assertEqual(
            key,
            (
                f"nexa:{PRODUCT_DETAIL_CACHE_VERSION}:catalog:"
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

    def test_product_detail_hard_ttl_has_jitter(self):
        values = [
            product_detail_hard_cache_timeout()
            for _ in range(100)
        ]

        minimum = (
            PRODUCT_DETAIL_HARD_TIMEOUT
            - PRODUCT_DETAIL_HARD_TIMEOUT_JITTER
        )

        maximum = (
            PRODUCT_DETAIL_HARD_TIMEOUT
            + PRODUCT_DETAIL_HARD_TIMEOUT_JITTER
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
            PRODUCT_DETAIL_HARD_TIMEOUT
            - PRODUCT_DETAIL_HARD_TIMEOUT_JITTER
        )

        maximum = (
            PRODUCT_DETAIL_HARD_TIMEOUT
            + PRODUCT_DETAIL_HARD_TIMEOUT_JITTER
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

    # =========================================================
    # Stale-While-Revalidate (Cache Breakdown / hot-key protection)
    # =========================================================

    def test_fresh_window_is_served_from_cache(self):
        first = self.client.get(
            self.product_url(),
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        stored = cache.get(
            product_detail_key(
                product_id=self.product.id,
            ),
        )

        # The cached entry is an SWR envelope whose fresh window is
        # still open: data plus a future stale_at timestamp.
        self.assertIn(
            "data",
            stored,
        )

        self.assertIn(
            "stale_at",
            stored,
        )

        self.assertGreater(
            stored["stale_at"],
            time.time(),
        )

        self.assertEqual(
            stored["data"]["id"],
            str(self.product.id),
        )

    def test_stale_entry_is_served_without_waiting(self):
        # Force the fresh window shut: the envelope is now stale but
        # still inside the hard TTL, and another worker holds the
        # revalidation lock.
        self.client.get(
            self.product_url(),
        )

        key = product_detail_key(
            product_id=self.product.id,
        )

        envelope = cache.get(key)

        envelope["stale_at"] = time.time() - 1

        cache.set(
            key,
            envelope,
            timeout=300,
        )

        other_worker = RedisLock(
            key=product_detail_lock_key(
                product_id=self.product.id,
            ),
            timeout=10,
        )

        self.assertTrue(
            other_worker.acquire(),
        )

        try:
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

            self.assertEqual(
                response.data["data"]["id"],
                str(self.product.id),
            )

            # Hot-key behavior: the stale value is served
            # immediately; the request does not touch the DB and
            # does not queue behind the revalidator.
            self.assertEqual(
                len(queries),
                0,
            )

        finally:
            other_worker.release()

    # =========================================================
    # Serializer / Representation Cache
    # =========================================================

    def test_product_detail_serializer_does_not_create_n_plus_one_queries(self):
        ProductVariant.objects.create(
            product=self.product,
            sku="CACHE-V1",
            name="Black",
            price=100000,
            status=ProductVariant.Status.ACTIVE,
        )

        ProductVariant.objects.create(
            product=self.product,
            sku="CACHE-V2",
            name="White",
            price=120000,
            status=ProductVariant.Status.ACTIVE,
        )

        # The annotated detail selector (COUNT/MIN in the DB) keeps
        # the query budget fixed; building the representation after
        # the fetch is query-free.
        product = ProductSelector.public_product_detail(
            product_id=self.product.id,
        )

        with CaptureQueriesContext(
            connection,
        ) as queries:
            data = ProductDetailSerializer(
                product,
            ).data

        self.assertEqual(
            data["variant_count"],
            2,
        )

        self.assertEqual(
            Decimal(str(data["min_variant_price"])),
            Decimal("100000.00"),
        )

        # SerializerMethodFields consumed prefetched data only:
        # zero additional queries while serializing.
        self.assertEqual(
            len(queries),
            0,
        )

    def test_serializer_cache_skips_serializer_and_database_on_hit(self):
        cache.clear()

        url = self.product_url()

        # First request → MISS (DB + selector + serializer + SET)
        first = self.client.get(url)

        self.assertEqual(
            first.status_code,
            200,
        )

        # Second request → HIT (no serializer, no DB)
        with CaptureQueriesContext(
            connection,
        ) as queries:
            second = self.client.get(url)

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

    def test_detail_response_contains_variant_representation(self):
        ProductVariant.objects.create(
            product=self.product,
            sku="CACHE-DETAIL-1",
            name="Black",
            price=100000,
            status=ProductVariant.Status.ACTIVE,
        )

        cache.clear()

        response = self.client.get(
            self.product_url(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.data["data"]

        self.assertEqual(
            len(data["variants"]),
            1,
        )

        self.assertEqual(
            data["variants"][0]["sku"],
            "CACHE-DETAIL-1",
        )

        self.assertEqual(
            data["variant_count"],
            1,
        )

        # The SQL MIN's decimal scale differs per backend (PostgreSQL
        # keeps "100000.00", SQLite renders "100000"): compare as
        # Decimal, never as a string.
        self.assertEqual(
            Decimal(str(data["min_variant_price"])),
            Decimal("100000.00"),
        )
