from decimal import Decimal

from django.test import TestCase

from apps.payments.gateways import MockPaymentGateway
from apps.payments.models import Payment, PaymentAttempt
from apps.payments.services import PaymentService

from apps.orders.models import Order
from apps.tenants.models import Tenant, Shop

from django.contrib.auth import get_user_model


User = get_user_model()


class PaymentGatewayTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="gateway@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Gateway Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Gateway Shop",
            slug="gateway-shop",
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

        cls.payment = Payment.objects.create(
            order=cls.order,
            user=cls.user,
            amount=Decimal("1000000"),
            currency="IRR",
        )

    def test_mock_gateway_initiates_payment(self):
        gateway = MockPaymentGateway()

        attempt = PaymentService.initiate_attempt(
            payment=self.payment,
            provider=gateway.name,
            idempotency_key="GATEWAY-001",
            gateway=gateway,
        )

        self.assertEqual(
            attempt.provider,
            "mock",
        )

        self.assertTrue(
            attempt.provider_reference.startswith(
                "MOCK-",
            )
        )

        self.assertEqual(
            attempt.status,
            PaymentAttempt.Status.REDIRECT_REQUIRED,
        )

        self.assertIn(
            "redirect_url",
            attempt.provider_response,
        )

    def test_gateway_attempt_is_idempotent(self):
        gateway = MockPaymentGateway()

        attempt1 = PaymentService.initiate_attempt(
            payment=self.payment,
            provider=gateway.name,
            idempotency_key="GATEWAY-IDEMPOTENT",
            gateway=gateway,
        )

        attempt2 = PaymentService.initiate_attempt(
            payment=self.payment,
            provider=gateway.name,
            idempotency_key="GATEWAY-IDEMPOTENT",
            gateway=gateway,
        )

        self.assertEqual(
            attempt1.id,
            attempt2.id,
        )

        self.assertEqual(
            PaymentAttempt.objects.filter(
                payment=self.payment,
            ).count(),
            1,
        )

    def test_mock_gateway_verifies_success(self):
        gateway = MockPaymentGateway()

        attempt = PaymentService.create_attempt(
            payment=self.payment,
            provider=gateway.name,
            idempotency_key="VERIFY-001",
        )

        result = gateway.verify_payment(
            attempt=attempt,
            payload={
                "status": "success",
                "transaction_id": "MOCK-TX-001",
            },
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.provider_transaction_id,
            "MOCK-TX-001",
        )

    def test_mock_gateway_verifies_failure(self):
        gateway = MockPaymentGateway()

        attempt = PaymentService.create_attempt(
            payment=self.payment,
            provider=gateway.name,
            idempotency_key="VERIFY-002",
        )

        result = gateway.verify_payment(
            attempt=attempt,
            payload={
                "status": "failed",
                "failure_code": "DECLINED",
                "failure_message": "Card declined.",
            },
        )

        self.assertFalse(result.success)

        self.assertEqual(
            result.failure_code,
            "DECLINED",
        )