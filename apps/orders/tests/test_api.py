from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.tenants.models import (
    Shop,
    Tenant,
    TenantMembership,
)


User = get_user_model()


class OrderAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(
            email="customer@example.com",
            password="test-password",
        )

        cls.other_customer = User.objects.create_user(
            email="other-customer@example.com",
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

        cls.tenant = Tenant.objects.create(
            name="Order Tenant",
        )

        cls.other_tenant = Tenant.objects.create(
            name="Other Order Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Order Shop",
            slug="order-shop",
        )

        cls.other_shop = Shop.objects.create(
            tenant=cls.other_tenant,
            name="Other Order Shop",
            slug="other-order-shop",
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

        cls.customer_order = Order.objects.create(
            shop=cls.shop,
            user=cls.customer,
            status=Order.Status.PAYMENT_PENDING,
            currency="IRR",
            subtotal=Decimal("1000000"),
            discount=Decimal("0"),
            shipping_cost=Decimal("0"),
            total=Decimal("1000000"),
            shipping_address={},
            billing_address={},
            customer_note="",
        )

        cls.other_customer_order = Order.objects.create(
            shop=cls.shop,
            user=cls.other_customer,
            status=Order.Status.PAYMENT_PENDING,
            currency="IRR",
            subtotal=Decimal("500000"),
            discount=Decimal("0"),
            shipping_cost=Decimal("0"),
            total=Decimal("500000"),
            shipping_address={},
            billing_address={},
            customer_note="",
        )

        cls.other_shop_order = Order.objects.create(
            shop=cls.other_shop,
            user=cls.customer,
            status=Order.Status.PAYMENT_PENDING,
            currency="IRR",
            subtotal=Decimal("700000"),
            discount=Decimal("0"),
            shipping_cost=Decimal("0"),
            total=Decimal("700000"),
            shipping_address={},
            billing_address={},
            customer_note="",
        )

    def setUp(self):
        self.client = APIClient()

    def test_customer_can_list_own_orders(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            "/api/v1/orders/",
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
            str(self.customer_order.id),
            ids,
        )

        self.assertNotIn(
            str(self.other_customer_order.id),
            ids,
        )

    def test_customer_can_retrieve_own_order(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            f"/api/v1/orders/"
            f"{self.customer_order.id}/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(self.customer_order.id),
        )

    def test_customer_cannot_retrieve_other_customers_order(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            f"/api/v1/orders/"
            f"{self.other_customer_order.id}/",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_manager_can_list_shop_orders(self):
        self.client.force_authenticate(
            user=self.manager,
        )

        response = self.client.get(
            f"/api/v1/orders/manage/shops/"
            f"{self.shop.id}/",
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
            str(self.customer_order.id),
            ids,
        )

        self.assertIn(
            str(self.other_customer_order.id),
            ids,
        )

        self.assertNotIn(
            str(self.other_shop_order.id),
            ids,
        )

    def test_manager_can_retrieve_shop_order(self):
        self.client.force_authenticate(
            user=self.manager,
        )

        response = self.client.get(
            f"/api/v1/orders/manage/shops/"
            f"{self.shop.id}/"
            f"{self.customer_order.id}/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_employee_cannot_manage_shop_orders(self):
        self.client.force_authenticate(
            user=self.employee,
        )

        response = self.client.get(
            f"/api/v1/orders/manage/shops/"
            f"{self.shop.id}/",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_other_tenant_manager_cannot_access_shop_orders(self):
        other_manager = User.objects.create_user(
            email="other-manager@example.com",
            password="test-password",
        )

        TenantMembership.objects.create(
            user=other_manager,
            tenant=self.other_tenant,
            role=TenantMembership.Role.MANAGER,
        )

        self.client.force_authenticate(
            user=other_manager,
        )

        response = self.client.get(
            f"/api/v1/orders/manage/shops/"
            f"{self.shop.id}/",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_customer_cannot_create_order_directly(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            "/api/v1/orders/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_customer_cannot_update_order_directly(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.patch(
            f"/api/v1/orders/"
            f"{self.customer_order.id}/",
            {
                "total": "1.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_anonymous_user_cannot_access_orders(self):
        response = self.client.get(
            "/api/v1/orders/",
        )

        self.assertEqual(
            response.status_code,
            401,
        )
