from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Product
from apps.tenants.models import (
    Shop,
    Tenant,
    TenantMembership,
)


User = get_user_model()


class ProductManagementPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="owner@example.com",
            password="test-password",
        )

        cls.manager = User.objects.create_user(
            email="manager@example.com",
            password="test-password",
        )

        cls.employee = User.objects.create_user(
            email="employee@example.com",
            password="test-password",
        )

        cls.other_user = User.objects.create_user(
            email="other@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Tenant A",
        )

        cls.other_tenant = Tenant.objects.create(
            name="Tenant B",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Shop A",
            slug="shop-a",
        )

        cls.other_shop = Shop.objects.create(
            tenant=cls.other_tenant,
            name="Shop B",
            slug="shop-b",
        )

        TenantMembership.objects.create(
            user=cls.owner,
            tenant=cls.tenant,
            role=TenantMembership.Role.OWNER,
        )

        TenantMembership.objects.create(
            user=cls.manager,
            tenant=cls.tenant,
            role=TenantMembership.Role.MANAGER,
        )

        TenantMembership.objects.create(
            user=cls.employee,
            tenant=cls.tenant,
            role=TenantMembership.Role.EMPLOYEE,
        )

        TenantMembership.objects.create(
            user=cls.other_user,
            tenant=cls.other_tenant,
            role=TenantMembership.Role.OWNER,
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Product A",
            slug="product-a",
            status=Product.Status.ACTIVE,
        )

        cls.other_product = Product.objects.create(
            shop=cls.other_shop,
            name="Product B",
            slug="product-b",
            status=Product.Status.ACTIVE,
        )

    def setUp(self):
        self.client = APIClient()

    def url(self):
        return (
            f"/api/v1/catalog/manage/shops/"
            f"{self.shop.id}/products/"
        )

    def test_owner_can_list_products(self):
        self.client.force_authenticate(
            user=self.owner,
        )

        response = self.client.get(
            self.url(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertIn(
            str(self.product.id),
            ids,
        )

    def test_manager_can_create_product(self):
        self.client.force_authenticate(
            user=self.manager,
        )

        response = self.client.post(
            self.url(),
            {
                "name": "New Product",
                "slug": "new-product",
                "description": "Created by manager",
                "status": Product.Status.DRAFT,
                "brand": None,
                "categories": [],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            Product.objects.filter(
                shop=self.shop,
                slug="new-product",
            ).exists()
        )

    def test_employee_cannot_create_product(self):
        self.client.force_authenticate(
            user=self.employee,
        )

        response = self.client.post(
            self.url(),
            {
                "name": "Forbidden Product",
                "slug": "forbidden-product",
                "status": Product.Status.DRAFT,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_other_tenant_cannot_list_shop_products(self):
        self.client.force_authenticate(
            user=self.other_user,
        )

        response = self.client.get(
            self.url(),
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_user_cannot_access_product_from_other_shop(self):
        self.client.force_authenticate(
            user=self.owner,
        )

        response = self.client.get(
            f"/api/v1/catalog/manage/shops/"
            f"{self.shop.id}/products/"
            f"{self.other_product.id}/",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_anonymous_user_cannot_manage_products(self):
        response = self.client.get(
            self.url(),
        )

        self.assertEqual(
            response.status_code,
            401,
        )