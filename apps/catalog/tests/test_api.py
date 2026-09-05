from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import (
    Shop,
    Tenant,
    TenantMembership,
)


User = get_user_model()


class ProductAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.manager = User.objects.create_user(
            email="manager@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="API Tenant",
        )

        cls.other_tenant = Tenant.objects.create(
            name="Other API Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="API Shop",
            slug="api-shop",
        )

        cls.other_shop = Shop.objects.create(
            tenant=cls.other_tenant,
            name="Other API Shop",
            slug="other-api-shop",
        )

        TenantMembership.objects.create(
            user=cls.manager,
            tenant=cls.tenant,
            role=TenantMembership.Role.MANAGER,
        )

        cls.active_product = Product.objects.create(
            shop=cls.shop,
            name="Active Product",
            slug="active-product",
            status=Product.Status.ACTIVE,
        )

        cls.draft_product = Product.objects.create(
            shop=cls.shop,
            name="Draft Product",
            slug="draft-product",
            status=Product.Status.DRAFT,
        )

        cls.other_product = Product.objects.create(
            shop=cls.other_shop,
            name="Other Product",
            slug="other-product",
            status=Product.Status.ACTIVE,
        )

    def test_product_list_returns_active_products_only(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data["results"]
        }

        self.assertIn(
            str(self.active_product.id),
            ids,
        )

        self.assertIn(
            str(self.other_product.id),
            ids,
        )

        self.assertNotIn(
            str(self.draft_product.id),
            ids,
        )

    def test_draft_product_is_not_public(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
        )

        ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertNotIn(
            str(self.draft_product.id),
            ids,
        )

    def test_retrieve_active_product(self):
        response = self.client.get(
            f"/api/v1/catalog/products/{self.active_product.id}/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(self.active_product.id),
        )

    def test_retrieve_draft_product_returns_404(self):
        response = self.client.get(
            f"/api/v1/catalog/products/{self.draft_product.id}/",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_product_endpoint_is_read_only(self):
        response = self.client.post(
            "/api/v1/catalog/products/",
            {
                "name": "Hacked Product",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    # =========================================================
    # Filtering / Search / Ordering
    # =========================================================

    def test_filter_by_status(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "status": Product.Status.ACTIVE,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data["results"]
        }

        self.assertIn(
            str(self.active_product.id),
            ids,
        )

    def test_search_by_name(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "Active",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

    def test_search_by_variant_sku(self):
        ProductVariant.objects.create(
            product=self.active_product,
            sku="NIKE-AIR-001",
            name="Nike Air",
            price=Decimal("1000000"),
            status=ProductVariant.Status.ACTIVE,
        )

        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "search": "NIKE-AIR-001",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

    def test_ordering_by_name(self):
        Product.objects.create(
            shop=self.shop,
            name="AAA Product",
            slug="aaa-product",
            status=Product.Status.ACTIVE,
        )

        Product.objects.create(
            shop=self.shop,
            name="ZZZ Product",
            slug="zzz-product",
            status=Product.Status.ACTIVE,
        )

        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "ordering": "name",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        names = [
            item["name"]
            for item in response.data["results"]
        ]

        self.assertEqual(
            names,
            sorted(names),
        )

    def test_descending_ordering(self):
        Product.objects.create(
            shop=self.shop,
            name="AAA Product",
            slug="aaa-product",
            status=Product.Status.ACTIVE,
        )

        Product.objects.create(
            shop=self.shop,
            name="ZZZ Product",
            slug="zzz-product",
            status=Product.Status.ACTIVE,
        )

        response = self.client.get(
            "/api/v1/catalog/products/",
            {
                "ordering": "-name",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        names = [
            item["name"]
            for item in response.data["results"]
        ]

        self.assertEqual(
            names,
            sorted(
                names,
                reverse=True,
            ),
        )

    def test_filter_cannot_escape_tenant_scope(self):
        client = APIClient()
        client.force_authenticate(
            user=self.manager,
        )

        response = client.get(
            f"/api/v1/catalog/manage/"
            f"shops/{self.shop.id}/products/",
            {
                "shop": str(self.other_shop.id),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            item["id"]
            for item in response.data["results"]
        }

        self.assertNotIn(
            str(self.other_product.id),
            ids,
        )