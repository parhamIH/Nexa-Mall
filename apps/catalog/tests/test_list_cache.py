from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.http import QueryDict
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.catalog.cache import (
    bump_product_list_namespace,
    product_list_key,
    product_list_namespace_version,
)
from apps.catalog.models import Product
from apps.catalog.services.product import ProductService
from apps.tenants.models import Shop, Tenant, TenantMembership


User = get_user_model()


def query_dict(**params):
    qdict = QueryDict(mutable=True)

    for name, value in params.items():
        qdict.appendlist(name, value)

    return qdict


class ProductListCacheKeyTests(TestCase):

    def setUp(self):
        cache.clear()

    def test_same_query_has_same_key(self):
        params = query_dict(
            search="nike",
            cursor="abc123",
            page_size="20",
        )

        self.assertEqual(
            product_list_key(query_params=params),
            product_list_key(query_params=params),
        )

    def test_query_parameter_order_does_not_change_key(self):
        one = query_dict(search="nike", cursor="abc123", page_size="20")

        two = query_dict(page_size="20", cursor="abc123", search="nike")

        self.assertEqual(
            product_list_key(query_params=one),
            product_list_key(query_params=two),
        )

    def test_different_query_has_different_key(self):
        one = query_dict(search="nike")

        two = query_dict(search="adidas")

        self.assertNotEqual(
            product_list_key(query_params=one),
            product_list_key(query_params=two),
        )

    def test_different_api_versions_have_different_keys(self):
        params = query_dict(search="nike")

        self.assertNotEqual(
            product_list_key(query_params=params, version="v1"),
            product_list_key(query_params=params, version="v2"),
        )

    def test_different_cursors_use_different_cache_keys(self):
        one = query_dict(cursor="cursor-a")

        two = query_dict(cursor="cursor-b")

        self.assertNotEqual(
            product_list_key(query_params=one),
            product_list_key(query_params=two),
        )

    def test_page_parameter_no_longer_mints_keys(self):
        # Under cursor pagination `page` is an unknown parameter: it
        # must be ignored by the cache key (no orphan entries).
        one = query_dict(search="nike")

        two = query_dict(search="nike")
        two.appendlist("page", "2")

        self.assertEqual(
            product_list_key(query_params=one),
            product_list_key(query_params=two),
        )

    def test_irrelevant_query_parameter_does_not_change_key(self):
        one = query_dict(search="nike")

        two = query_dict(search="nike")
        two.appendlist("unused", "123")

        self.assertEqual(
            product_list_key(query_params=one),
            product_list_key(query_params=two),
        )

    def test_search_algorithm_version_changes_cache_key(self):
        # Cache SCHEMA version (v2) is embedded in the key and is a
        # DIFFERENT axis from the API URL version: the same /api/v1/
        # endpoint moved from the unranked (v1) to the ranked (v2)
        # representation, and the two must never share cache keys.
        one = query_dict(search="nike")

        key = product_list_key(
            query_params=one,
            version="v1",
        )

        self.assertIn(
            ":v2:",
            key,
        )

    def test_namespace_bump_changes_list_cache_key(self):
        params = query_dict(search="nike")

        old_key = product_list_key(
            query_params=params,
        )

        cache.set(
            old_key,
            {
                "data": [],
                "meta": {
                    "count": 0,
                },
            },
            timeout=300,
        )

        old_namespace = product_list_namespace_version()

        new_namespace = bump_product_list_namespace()

        self.assertEqual(
            new_namespace,
            old_namespace + 1,
        )

        new_key = product_list_key(
            query_params=params,
        )

        # Lazy invalidation: the old entry may still physically
        # exist, but no request can reach it through the new key.
        self.assertNotEqual(
            old_key,
            new_key,
        )

        self.assertIsNone(
            cache.get(new_key),
        )


class ProductListCacheAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(
            email="list-manager@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="List Cache Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="List Cache Shop",
            slug="list-cache-shop",
        )

        TenantMembership.objects.create(
            user=cls.manager,
            tenant=cls.tenant,
            role=TenantMembership.Role.MANAGER,
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Nike Air",
            slug="nike-air",
            description="Nike product",
            status=Product.Status.ACTIVE,
        )

    def setUp(self):
        cache.clear()

        self.client = APIClient()

    def test_second_list_request_is_cache_hit(self):
        url = "/api/v1/catalog/products/"

        first = self.client.get(url)

        self.assertEqual(
            first.status_code,
            200,
        )

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

    def test_different_query_uses_different_cache_key(self):
        one = query_dict(search="nike")

        two = query_dict(search="adidas")

        self.assertNotEqual(
            product_list_key(query_params=one),
            product_list_key(query_params=two),
        )

    def test_product_mutation_invalidates_list_cache(self):
        url = "/api/v1/catalog/products/"

        # Warm the list cache: 1 item.
        first = self.client.get(url)

        self.assertEqual(
            first.status_code,
            200,
        )

        self.assertEqual(
            len(first.data["data"]),
            1,
        )

        # Second request proves the entry is served from cache.
        with CaptureQueriesContext(
            connection,
        ) as queries:
            second = self.client.get(url)

        self.assertEqual(
            len(queries),
            0,
        )

        # A new product changes the list representation. The
        # service runs on COMMIT: the detail invalidation deletes
        # its entry and the namespace bump makes ALL list keys
        # (every filter/search/cursor combination) unreachable.
        with self.captureOnCommitCallbacks(
            execute=True,
        ):
            ProductService.create_product(
                shop_id=self.shop.id,
                validated_data={
                    "name": "Adidas Run",
                    "slug": "adidas-run",
                    "description": "",
                    "status": Product.Status.ACTIVE,
                    "brand": None,
                },
                user=self.manager,
            )

        third = self.client.get(url)

        self.assertEqual(
            third.status_code,
            200,
        )

        # Fresh data - not the stale cached page.
        self.assertEqual(
            len(third.data["data"]),
            2,
        )

    def test_stale_list_entry_is_not_served_after_bump(self):
        url = "/api/v1/catalog/products/"

        warm = self.client.get(url)

        self.assertEqual(
            len(warm.data["data"]),
            1,
        )

        # Simulate the committed mutation path directly: the
        # namespace bump is what makes the warm entry unreachable.
        bump_product_list_namespace()

        after_bump = self.client.get(url)

        self.assertEqual(
            after_bump.status_code,
            200,
        )

        self.assertEqual(
            len(after_bump.data["data"]),
            1,
        )
