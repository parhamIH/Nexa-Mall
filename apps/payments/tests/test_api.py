from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
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
    PaymentTransaction,
    WebhookEvent,
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

    # =========================================================
    # Webhooks
    # =========================================================

    def test_webhook_endpoint_does_not_require_authentication(self):
        response = self.client.post(
            "/api/v1/payments/webhooks/mock/",
            {
                "event_id": "API-EVENT-001",
                "event_type": "payment.failed",
                "payload": {},
            },
            format="json",
        )

        self.assertNotEqual(
            response.status_code,
            401,
        )

    def test_success_webhook(self):
        order = self.create_order()

        payment = Payment.objects.create(
            order=order,
            user=self.user,
            amount=order.total,
            currency=order.currency,
        )

        attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="mock",
            idempotency_key="API-WEBHOOK-001",
            amount=payment.amount,
            currency=payment.currency,
            status=PaymentAttempt.Status.INITIATED,
            provider_reference="MOCK-REF-001",
        )

        response = self.client.post(
            "/api/v1/payments/webhooks/mock/",
            {
                "event_id": "API-EVENT-SUCCESS",
                "event_type": "payment.succeeded",
                "payload": {
                    "provider_reference": "MOCK-REF-001",
                    "status": "success",
                    "transaction_id": "API-TX-001",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCEEDED,
        )

    def test_duplicate_webhook_http_is_idempotent(self):
        order = self.create_order()

        payment = Payment.objects.create(
            order=order,
            user=self.user,
            amount=order.total,
            currency=order.currency,
        )

        PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="mock",
            idempotency_key="API-WEBHOOK-IDEMPOTENT-001",
            amount=payment.amount,
            currency=payment.currency,
            status=PaymentAttempt.Status.INITIATED,
            provider_reference="MOCK-IDEMPOTENT-REF",
        )

        payload = {
            "event_id": "API-EVENT-IDEMPOTENT",
            "event_type": "payment.succeeded",
            "payload": {
                "provider_reference": "MOCK-IDEMPOTENT-REF",
                "status": "success",
                "transaction_id": "API-TX-IDEMPOTENT",
            },
        }

        first = self.client.post(
            "/api/v1/payments/webhooks/mock/",
            payload,
            format="json",
        )

        second = self.client.post(
            "/api/v1/payments/webhooks/mock/",
            payload,
            format="json",
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertEqual(
            WebhookEvent.objects.filter(
                provider="mock",
                event_id="API-EVENT-IDEMPOTENT",
            ).count(),
            1,
        )

        self.assertEqual(
            PaymentTransaction.objects.filter(
                payment=payment,
                transaction_type=PaymentTransaction.Type.CAPTURE,
            ).count(),
            1,
        )

    def test_unknown_webhook_provider_is_rejected(self):
        response = self.client.post(
            "/api/v1/payments/webhooks/unknown/",
            {
                "event_id": "UNKNOWN-EVENT",
                "event_type": "payment.succeeded",
                "payload": {},
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    @staticmethod
    def _throttle_payment_requests():
        from apps.api.throttling import PaymentRateThrottle

        PaymentRateThrottle.rate = "2/min"

    def test_payment_endpoint_is_throttled(self):
        cache.clear()

        self._throttle_payment_requests()

        from apps.api.throttling import PaymentRateThrottle

        self.addCleanup(
            setattr,
            PaymentRateThrottle,
            "rate",
            None,
        )
        self.addCleanup(cache.clear)

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

        third = self.client.post(
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
            third.status_code,
            429,
        )
