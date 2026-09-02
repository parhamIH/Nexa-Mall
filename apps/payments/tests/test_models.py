from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.orders.models import Order
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentTransaction,
    WebhookEvent,
)
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class PaymentModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="payment@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Payment Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Payment Shop",
            slug="payment-shop",
        )

        cls.order = Order.objects.create(
            shop=cls.shop,
            user=cls.user,
            status=Order.Status.PAYMENT_PENDING,
            currency="IRR",
            subtotal=Decimal("1000000"),
            discount=Decimal("0"),
            shipping_cost=Decimal("0"),
            total=Decimal("1000000"),
        )

    def test_create_payment(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        self.assertIsNotNone(payment.id)

        self.assertEqual(
            payment.order,
            self.order,
        )

        self.assertEqual(
            payment.user,
            self.user,
        )

        self.assertEqual(
            payment.amount,
            Decimal("1000000"),
        )

        self.assertEqual(
            payment.currency,
            "IRR",
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

    def test_payment_is_one_to_one_with_order(self):
        Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        with self.assertRaises(IntegrityError):
            Payment.objects.create(
                order=self.order,
                user=self.user,
                amount=Decimal("1000000"),
                currency="IRR",
            )

    def test_payment_attempt_can_be_created(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="test_gateway",
            idempotency_key="PAY-ATTEMPT-001",
            amount=Decimal("1000000"),
            currency="IRR",
        )

        self.assertEqual(
            attempt.payment,
            payment,
        )

        self.assertEqual(
            attempt.attempt_number,
            1,
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.INITIATED,
        )

    def test_payment_can_have_multiple_attempts(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        first_attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="test_gateway",
            idempotency_key="PAY-ATTEMPT-001",
            amount=Decimal("1000000"),
            currency="IRR",
            status=PaymentAttempt.Status.FAILED,
        )

        second_attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=2,
            provider="test_gateway",
            idempotency_key="PAY-ATTEMPT-002",
            amount=Decimal("1000000"),
            currency="IRR",
            status=PaymentAttempt.Status.SUCCEEDED,
        )

        self.assertEqual(
            payment.attempts.count(),
            2,
        )

        self.assertEqual(
            first_attempt.status,
            PaymentAttempt.Status.FAILED,
        )

        self.assertEqual(
            second_attempt.status,
            PaymentAttempt.Status.SUCCEEDED,
        )

    def test_attempt_number_must_be_unique_per_payment(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="test_gateway",
            idempotency_key="PAY-ATTEMPT-001",
            amount=Decimal("1000000"),
            currency="IRR",
        )

        with self.assertRaises(IntegrityError):
            PaymentAttempt.objects.create(
                payment=payment,
                attempt_number=1,
                provider="test_gateway",
                idempotency_key="PAY-ATTEMPT-002",
                amount=Decimal("1000000"),
                currency="IRR",
            )

    def test_idempotency_key_must_be_unique(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="test_gateway",
            idempotency_key="SAME-KEY",
            amount=Decimal("1000000"),
            currency="IRR",
        )

        with self.assertRaises(IntegrityError):
            PaymentAttempt.objects.create(
                payment=payment,
                attempt_number=2,
                provider="test_gateway",
                idempotency_key="SAME-KEY",
                amount=Decimal("1000000"),
                currency="IRR",
            )

    def test_payment_transaction_can_be_created(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="test_gateway",
            idempotency_key="PAY-ATTEMPT-TX-001",
            amount=Decimal("1000000"),
            currency="IRR",
            status=PaymentAttempt.Status.SUCCEEDED,
        )

        transaction = PaymentTransaction.objects.create(
            payment=payment,
            attempt=attempt,
            transaction_type=PaymentTransaction.Type.CAPTURE,
            amount=Decimal("1000000"),
            currency="IRR",
            status=PaymentTransaction.Status.SUCCEEDED,
            provider_transaction_id="TX-001",
        )

        self.assertEqual(
            transaction.payment,
            payment,
        )

        self.assertEqual(
            transaction.attempt,
            attempt,
        )

        self.assertEqual(
            transaction.transaction_type,
            PaymentTransaction.Type.CAPTURE,
        )

        self.assertEqual(
            transaction.status,
            PaymentTransaction.Status.SUCCEEDED,
        )

    def test_provider_transaction_id_must_be_unique(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

        attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            provider="test_gateway",
            idempotency_key="PAY-ATTEMPT-TX-002",
            amount=Decimal("1000000"),
            currency="IRR",
            status=PaymentAttempt.Status.SUCCEEDED,
        )

        PaymentTransaction.objects.create(
            payment=payment,
            attempt=attempt,
            transaction_type=PaymentTransaction.Type.CAPTURE,
            amount=Decimal("1000000"),
            currency="IRR",
            status=PaymentTransaction.Status.SUCCEEDED,
            provider_transaction_id="TX-UNIQUE",
        )

        with self.assertRaises(IntegrityError):
            PaymentTransaction.objects.create(
                payment=payment,
                attempt=attempt,
                transaction_type=PaymentTransaction.Type.REFUND,
                amount=Decimal("100000"),
                currency="IRR",
                status=PaymentTransaction.Status.SUCCEEDED,
                provider_transaction_id="TX-UNIQUE",
            )

    def test_webhook_event_can_be_created(self):
        event = WebhookEvent.objects.create(
            provider="test_gateway",
            event_id="EVENT-001",
            event_type="payment.succeeded",
            payload={
                "payment_id": str(self.order.id),
                "amount": "1000000",
            },
        )

        self.assertIsNotNone(event.id)

        self.assertEqual(
            event.provider,
            "test_gateway",
        )

        self.assertEqual(
            event.event_id,
            "EVENT-001",
        )

        self.assertEqual(
            event.status,
            WebhookEvent.Status.RECEIVED,
        )

    def test_webhook_event_provider_and_event_id_must_be_unique(self):
        WebhookEvent.objects.create(
            provider="test_gateway",
            event_id="EVENT-UNIQUE",
            event_type="payment.succeeded",
            payload={
                "test": True,
            },
        )

        with self.assertRaises(IntegrityError):
            WebhookEvent.objects.create(
                provider="test_gateway",
                event_id="EVENT-UNIQUE",
                event_type="payment.succeeded",
                payload={
                    "test": True,
                },
            )

    def test_same_event_id_can_exist_for_different_providers(self):
        first = WebhookEvent.objects.create(
            provider="gateway_a",
            event_id="EVENT-001",
            event_type="payment.succeeded",
            payload={},
        )

        second = WebhookEvent.objects.create(
            provider="gateway_b",
            event_id="EVENT-001",
            event_type="payment.succeeded",
            payload={},
        )

        self.assertNotEqual(
            first.provider,
            second.provider,
        )

        self.assertEqual(
            first.event_id,
            second.event_id,
        )