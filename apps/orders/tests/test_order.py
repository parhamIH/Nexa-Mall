from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from apps.orders.models import Order
from apps.orders.services.order import OrderService
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class OrderServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="customer@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Test Shop",
            slug="test-shop",
        )

    def test_create_order(self):
        order = OrderService.create_order(
            shop=self.shop,
            user=self.user,
        )

        self.assertIsNotNone(order.id)
        self.assertIsNotNone(order.order_number)

        self.assertEqual(
            order.shop,
            self.shop,
        )

        self.assertEqual(
            order.user,
            self.user,
        )

        self.assertEqual(
            order.status,
            Order.Status.PENDING,
        )

        self.assertEqual(
            order.currency,
            "IRR",
        )

        self.assertEqual(
            order.subtotal,
            Decimal("0"),
        )

        self.assertEqual(
            order.discount,
            Decimal("0"),
        )

        self.assertEqual(
            order.shipping_cost,
            Decimal("0"),
        )

        self.assertEqual(
            order.total,
            Decimal("0"),
        )
    def test_create_order_persists_in_database(self):
        order = OrderService.create_order(
            shop=self.shop,
            user=self.user,
        )

        self.assertTrue(
            Order.objects.filter(
                id=order.id,
            ).exists()
        )

    def test_create_order_belongs_to_correct_shop(self):
        order = OrderService.create_order(
            shop=self.shop,
            user=self.user,
        )

        self.assertEqual(
            order.shop_id,
            self.shop.id,
        )

    def test_create_order_belongs_to_correct_user(self):
        order = OrderService.create_order(
            shop=self.shop,
            user=self.user,
        )

        self.assertEqual(
            order.user_id,
            self.user.id,
        )
        