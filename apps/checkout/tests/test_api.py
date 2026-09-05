from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import InventoryItem, Reservation
from apps.orders.models import Order
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class CheckoutAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="checkout-api@example.com",
            password="test-password",
        )

        cls.other_user = User.objects.create_user(
            email="other-checkout@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Checkout API Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Checkout API Shop",
            slug="checkout-api-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Checkout API Product",
            slug="checkout-api-product",
            status=Product.Status.ACTIVE,
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="CHECKOUT-API-001",
            name="Test Variant",
            price=Decimal("500000"),
            status=ProductVariant.Status.ACTIVE,
        )

        cls.inventory = InventoryItem.objects.create(
            variant=cls.variant,
            on_hand=10,
            reserved=0,
        )

    def setUp(self):
        self.client = APIClient()

    def create_cart(
        self,
        *,
        quantity=2,
        user=None,
    ):
        cart = Cart.objects.create(
            user=user or self.user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=quantity,
        )

        return cart

    def checkout_url(self):
        return "/api/v1/checkout/"

    def test_anonymous_user_cannot_checkout(self):
        cart = self.create_cart()

        response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_user_can_checkout(self):
        self.client.force_authenticate(
            user=self.user,
        )

        cart = self.create_cart(
            quantity=2,
        )

        response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["status"],
            Order.Status.PAYMENT_PENDING,
        )

        self.assertEqual(
            response.data["subtotal"],
            "1000000.00",
        )

        self.assertEqual(
            len(response.data["items"]),
            1,
        )

        cart.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            cart.status,
            Cart.Status.CONVERTED,
        )

        self.assertEqual(
            self.inventory.reserved,
            2,
        )

    def test_checkout_returns_shipping_cost(self):
        self.client.force_authenticate(
            user=self.user,
        )

        cart = self.create_cart(
            quantity=2,
        )

        response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
                "shipping_cost": "50000",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["shipping_cost"],
            "50000.00",
        )

        self.assertEqual(
            response.data["total"],
            "1050000.00",
        )

    def test_empty_cart_is_rejected(self):
        self.client.force_authenticate(
            user=self.user,
        )

        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_user_cannot_checkout_other_users_cart(self):
        self.client.force_authenticate(
            user=self.user,
        )

        other_cart = self.create_cart(
            quantity=2,
            user=self.other_user,
        )

        response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(other_cart.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_insufficient_stock_rolls_back_checkout(self):
        self.client.force_authenticate(
            user=self.user,
        )

        cart = self.create_cart(
            quantity=11,
        )

        response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        cart.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            cart.status,
            Cart.Status.ACTIVE,
        )

        self.assertEqual(
            self.inventory.reserved,
            0,
        )

        self.assertFalse(
            Order.objects.filter(
                user=self.user,
            ).exists()
        )

        self.assertFalse(
            Reservation.objects.filter(
                inventory=self.inventory,
            ).exists()
        )

    def test_invalid_reservation_duration_is_rejected(self):
        self.client.force_authenticate(
            user=self.user,
        )

        cart = self.create_cart()

        response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
                "reservation_minutes": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_checkout_cannot_be_repeated(self):
        self.client.force_authenticate(
            user=self.user,
        )

        cart = self.create_cart()

        first_response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            201,
        )

        second_response = self.client.post(
            self.checkout_url(),
            {
                "cart_id": str(cart.id),
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            400,
        )

