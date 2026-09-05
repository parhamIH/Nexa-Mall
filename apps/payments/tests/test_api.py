from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.checkout.services import CheckoutService
from apps.inventory.models import InventoryItem
from apps.orders.models import Order
from apps.payments.models import (
    Payment,
    PaymentAttempt,
)
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class PaymentAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="payment-api@example.com",
            password="test-password",
        )

        cls.other_user = User.objects.create_user(
            email="other-payment-api@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Payment API Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Payment API Shop",
            slug="payment-api-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Payment API Product",
            slug="payment-api-product",
            status=Product.Status.ACTIVE,
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="PAY-API-001",
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

    def create_order(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=2,
        )

        return CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

    def test_anonymous_user_cannot_create_payment(self):
        order = self.create_order()

        response = self.client.post(
            "/api/v1/payments/",
            {
                "order_id": str(order.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_user_can_create_payment(self):
        self.client.force_authenticate(
            user=self.user,
        )

        order = self.create_order()

        response = self.client.post(
            "/api/v1/payments/",
            {
                "order_id": str(order.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["status"],
            Payment.Status.PENDING,
        )

        self.assertEqual(
            response.data["amount"],
            "1000000.00",
        )

        self.assertTrue(
            Payment.objects.filter(
                order=order,
                user=self.user,
            ).exists()
        )

    def test_create_payment_is_idempotent(self):
        self.client.force_authenticate(
            user=self.user,
        )

        order = self.create_order()

        first = self.client.post(
            "/api/v1/payments/",
            {
                "order_id": str(order.id),
            },
            format="json",
        )

        second = self.client.post(
            "/api/v1/payments/",
            {
                "order_id": str(order.id),
            },
            format="json",
        )

        self.assertEqual(
            first.status_code,
            201,
        )

        self.assertEqual(
            second.status_code,
            201,
        )

        self.assertEqual(
            first.data["id"],
            second.data["id"],
        )

    def test_user_can_create_payment_attempt(self):
        self.client.force_authenticate(
            user=self.user,
        )

        order = self.create_order()

        payment_response = self.client.post(
            "/api/v1/payments/",
            {
                "order_id": str(order.id),
            },
            format="json",
        )

        payment_id = payment_response.data["id"]

        response = self.client.post(
            f"/api/v1/payments/"
            f"{payment_id}/attempts/",
            {
                "provider": "mock",
                "idempotency_key": "API-ATTEMPT-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["attempt_number"],
            1,
        )

        self.assertEqual(
            response.data["provider"],
            "mock",
        )

        self.assertEqual(
            response.data["status"],
            PaymentAttempt.Status.REDIRECT_REQUIRED,
        )

        self.assertTrue(
            response.data["provider_reference"]
        )

    def test_payment_attempt_is_idempotent(self):
        self.client.force_authenticate(
            user=self.user,
        )

        order = self.create_order()

        payment_response = self.client.post(
            "/api/v1/payments/",
            {
                "order_id": str(order.id),
            },
            format="json",
        )

        payment_id = payment_response.data["id"]

        data = {
            "provider": "mock",
            "idempotency_key": "API-IDEMPOTENT",
        }

        first = self.client.post(
            f"/api/v1/payments/"
            f"{payment_id}/attempts/",
            data,
            format="json",
        )

        second = self.client.post(
            f"/api/v1/payments/"
            f"{payment_id}/attempts/",
            data,
            format="json",
        )

        self.assertEqual(
            first.status_code,
            201,
        )

        self.assertEqual(
            second.status_code,
            201,
        )

        self.assertEqual(
            first.data["id"],
            second.data["id"],
        )

    def test_user_can_get_own_payment(self):
        self.client.force_authenticate(
            user=self.user,
        )

        order = self.create_order()

        payment = Payment.objects.create(
            order=order,
            user=self.user,
            amount=order.total,
            currency=order.currency,
        )

        response = self.client.get(
            f"/api/v1/payments/"
            f"{payment.id}/",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(payment.id),
        )

    def test_user_cannot_get_other_users_payment(self):
        self.client.force_authenticate(
            user=self.user,
        )

        other_order = Order.objects.create(
            shop=self.shop,
            user=self.other_user,
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

        payment = Payment.objects.create(
            order=other_order,
            user=self.other_user,
            amount=other_order.total,
            currency=other_order.currency,
        )

        response = self.client.get(
            f"/api/v1/payments/"
            f"{payment.id}/",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_unsupported_provider_is_rejected(self):
        self.client.force_authenticate(
            user=self.user,
        )

        order = self.create_order()

        payment_response = self.client.post(
            "/api/v1/payments/",
            {
                "order_id": str(order.id),
            },
            format="json",
        )

        response = self.client.post(
            f"/api/v1/payments/"
            f"{payment_response.data['id']}/attempts/",
            {
                "provider": "unknown-provider",
                "idempotency_key": "UNKNOWN-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )
