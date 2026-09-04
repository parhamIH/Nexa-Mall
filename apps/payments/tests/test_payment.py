from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.checkout.services import CheckoutService
from apps.inventory.models import InventoryItem, Reservation
from apps.orders.models import Order
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentTransaction,
)
from apps.payments.services import PaymentService
from apps.tenants.models import Shop, Tenant


class PaymentServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        cls.user = User.objects.create_user(
            email="payment-service@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Payment Service Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Payment Service Shop",
            slug="payment-service-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Payment Product",
            slug="payment-product",
            status=Product.Status.ACTIVE,
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="PAYMENT-001",
            name="Test Variant",
            price=Decimal("500000"),
            status=ProductVariant.Status.ACTIVE,
        )

        cls.inventory = InventoryItem.objects.create(
            variant=cls.variant,
            on_hand=10,
            reserved=0,
        )

    def create_checkout_order(self, quantity=2):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=quantity,
        )

        return CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

    def test_create_payment(self):
        order = self.create_checkout_order()

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
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

    def test_create_payment_is_idempotent(self):
        order = self.create_checkout_order()

        payment1 = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        payment2 = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        self.assertEqual(
            payment1.id,
            payment2.id,
        )

        self.assertEqual(
            Payment.objects.filter(
                order=order,
            ).count(),
            1,
        )

    def test_create_attempt(self):
        order = self.create_checkout_order()

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        attempt = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="ATTEMPT-001",
        )

        self.assertEqual(
            attempt.attempt_number,
            1,
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.INITIATED,
        )

    def test_create_attempt_is_idempotent(self):
        order = self.create_checkout_order()

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        attempt1 = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="SAME-KEY",
        )

        attempt2 = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="SAME-KEY",
        )

        self.assertEqual(
            attempt1.id,
            attempt2.id,
        )

    def test_multiple_attempts(self):
        order = self.create_checkout_order()

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        attempt1 = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="ATTEMPT-001",
        )

        PaymentService.mark_failed(
            attempt=attempt1,
            failure_code="DECLINED",
            failure_message="Card declined.",
        )

        attempt2 = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="ATTEMPT-002",
        )

        self.assertEqual(
            attempt1.attempt_number,
            1,
        )

        self.assertEqual(
            attempt2.attempt_number,
            2,
        )

    def test_mark_processing(self):
        order = self.create_checkout_order()

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        attempt = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="PROCESS-001",
        )

        PaymentService.mark_processing(
            attempt=attempt,
        )

        attempt.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.PROCESSING,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PROCESSING,
        )

    def test_mark_failed(self):
        order = self.create_checkout_order()

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        attempt = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="FAIL-001",
        )

        PaymentService.mark_failed(
            attempt=attempt,
            failure_code="DECLINED",
            failure_message="Declined.",
        )

        attempt.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.FAILED,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.reserved,
            2,
        )

    def test_mark_success_confirms_payment_order_and_reservation(self):
        order = self.create_checkout_order()

        payment = PaymentService.create_payment(
            order=order,
            user=self.user,
        )

        attempt = PaymentService.create_attempt(
            payment=payment,
            provider="test_gateway",
            idempotency_key="SUCCESS-001",
        )

        PaymentService.mark_processing(
            attempt=attempt,
        )

        PaymentService.mark_success(
            attempt=attempt,
            provider_transaction_id="TX-SUCCESS-001",
            provider_response={
                "gateway": "test",
                "status": "success",
            },
        )

        payment.refresh_from_db()
        order.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCEEDED,
        )

        self.assertIsNotNone(
            payment.paid_at,
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
                transaction_type=PaymentTransaction.Type.CAPTURE,
                status=PaymentTransaction.Status.SUCCEEDED,
                provider_transaction_id="TX-SUCCESS-001",
            ).exists()
        )

        self.assertTrue(
            Reservation.objects.filter(
                order=order,
                status=Reservation.Status.CONFIRMED,
            ).exists()
        )

    def test_cannot_create_payment_for_wrong_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        other_user = User.objects.create_user(
            email="other-payment@example.com",
            password="test-password",
        )

        order = self.create_checkout_order()

        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                order=order,
                user=other_user,
            )

    def test_cannot_pay_non_payment_pending_order(self):
        order = self.create_checkout_order()

        order.status = Order.Status.CANCELLED
        order.save(
            update_fields=["status"],
        )

        with self.assertRaises(ValidationError):
            PaymentService.create_payment(
                order=order,
                user=self.user,
            )