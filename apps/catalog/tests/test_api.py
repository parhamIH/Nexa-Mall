from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import Shop, Tenant


class ProductAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.tenant = Tenant.objects.create(
            name="API Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="API Shop",
            slug="api-shop",
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

    def test_product_list_returns_active_products_only(self):
        response = self.client.get(
            "/api/v1/catalog/products/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.active_product.id),
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