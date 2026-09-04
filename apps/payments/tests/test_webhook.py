from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.checkout.services import CheckoutService
from apps.inventory.models import InventoryItem, Reservation
from apps.orders.models import Order
from apps.payments.gateways import MockPaymentGateway
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentTransaction,
    WebhookEvent,
)
from apps.payments.services import PaymentService
from apps.payments.services.webhook import WebhookService
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class WebhookServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="webhook@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Webhook Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Webhook Shop",
            slug="webhook-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Webhook Product",
            slug="webhook-product",
            status=Product.Status.ACTIVE,
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="WEBHOOK-001",
            name="Test Variant",
            price=Decimal("500000"),
            status=ProductVariant.Status.ACTIVE,
        )

        cls.inventory = InventoryItem.objects.create(
            variant=cls.variant,
            on_hand=10,
            reserved=0,
        )

        cls.gateway = MockPaymentGateway()

    def create_payment_flow(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=2,
        )

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        attempt = PaymentService.initiate_attempt(
            payment=payment,
            provider=self.gateway.name,
            idempotency_key="WEBHOOK-ATTEMPT-001",
            gateway=self.gateway,
        )

        return order, payment, attempt

    def test_success_webhook(self):
        order, payment, attempt = self.create_payment_flow()

        event = WebhookService.process(
            provider="mock",
            event_id="EVENT-001",
            event_type="payment.succeeded",
            payload={
                "provider_reference": attempt.provider_reference,
                "status": "success",
                "transaction_id": "TX-WEBHOOK-001",
            },
            gateway=self.gateway,
        )

        event.refresh_from_db()
        payment.refresh_from_db()
        order.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            event.status,
            WebhookEvent.Status.PROCESSED,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCEEDED,
        )

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            self.inventory.on_hand,
            8,
        )

        self.assertEqual(
            self.inventory.reserved,
            0,
        )

        self.assertTrue(
            PaymentTransaction.objects.filter(
                payment=payment,
                provider_transaction_id="TX-WEBHOOK-001",
                status=PaymentTransaction.Status.SUCCEEDED,
            ).exists()
        )

    def test_failed_webhook(self):
        order, payment, attempt = self.create_payment_flow()

        event = WebhookService.process(
            provider="mock",
            event_id="EVENT-002",
            event_type="payment.failed",
            payload={
                "provider_reference": attempt.provider_reference,
                "status": "failed",
                "failure_code": "DECLINED",
                "failure_message": "Payment declined.",
            },
            gateway=self.gateway,
        )

        event.refresh_from_db()
        payment.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(
            event.status,
            WebhookEvent.Status.PROCESSED,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.FAILED,
        )

    def test_duplicate_webhook_is_idempotent(self):
        order, payment, attempt = self.create_payment_flow()

        payload = {
            "provider_reference": attempt.provider_reference,
            "status": "success",
            "transaction_id": "TX-IDEMPOTENT-001",
        }

        WebhookService.process(
            provider="mock",
            event_id="EVENT-IDEMPOTENT",
            event_type="payment.succeeded",
            payload=payload,
            gateway=self.gateway,
        )

        WebhookService.process(
            provider="mock",
            event_id="EVENT-IDEMPOTENT",
            event_type="payment.succeeded",
            payload=payload,
            gateway=self.gateway,
        )

        self.assertEqual(
            WebhookEvent.objects.filter(
                provider="mock",
                event_id="EVENT-IDEMPOTENT",
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

    def test_unknown_payment_reference_is_ignored(self):
        event = WebhookService.process(
            provider="mock",
            event_id="EVENT-UNKNOWN",
            event_type="payment.succeeded",
            payload={
                "provider_reference": "UNKNOWN-REFERENCE",
                "status": "success",
                "transaction_id": "TX-UNKNOWN",
            },
            gateway=self.gateway,
        )

        event.refresh_from_db()

        self.assertEqual(
            event.status,
            WebhookEvent.Status.IGNORED,
        )

    def test_success_without_transaction_id_fails(self):
        order, payment, attempt = self.create_payment_flow()

        with self.assertRaises(Exception):
            WebhookService.process(
                provider="mock",
                event_id="EVENT-NO-TX",
                event_type="payment.succeeded",
                payload={
                    "provider_reference": attempt.provider_reference,
                    "status": "success",
                },
                gateway=self.gateway,
            )

        payment.refresh_from_db()

        self.assertNotEqual(
            payment.status,
            Payment.Status.SUCCEEDED,
        )