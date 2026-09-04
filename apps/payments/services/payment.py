from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import Reservation
from apps.inventory.services.reservation import ReservationService
from apps.orders.models import Order
from apps.orders.services.order import OrderService
from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentTransaction,
)


class PaymentService:

    @staticmethod
    @transaction.atomic
    def create_payment(
        *,
        order,
        user,
    ):
        if order.user_id != user.id:
            raise ValidationError(
                "Order does not belong to this user."
            )

        if order.status != Order.Status.PAYMENT_PENDING:
            raise ValidationError(
                "Order is not ready for payment."
            )

        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "user": user,
                "amount": order.total,
                "currency": order.currency,
                "status": Payment.Status.PENDING,
            },
        )

        if not created:
            if payment.user_id != user.id:
                raise ValidationError(
                    "Payment does not belong to this user."
                )

            if payment.amount != order.total:
                raise ValidationError(
                    "Payment amount does not match order total."
                )

            if payment.currency != order.currency:
                raise ValidationError(
                    "Payment currency does not match order currency."
                )

        return payment

    @staticmethod
    @transaction.atomic
    def create_attempt(
        *,
        payment,
        provider,
        idempotency_key,
    ):
        payment = (
            Payment.objects
            .select_for_update()
            .get(id=payment.id)
        )

        if payment.status == Payment.Status.SUCCEEDED:
            raise ValidationError(
                "Payment has already succeeded."
            )

        existing = PaymentAttempt.objects.filter(
            idempotency_key=idempotency_key,
        ).first()

        if existing:
            if existing.payment_id != payment.id:
                raise ValidationError(
                    "Idempotency key belongs to another payment."
                )

            return existing

        last_attempt = (
            PaymentAttempt.objects
            .filter(payment=payment)
            .order_by("-attempt_number")
            .first()
        )

        attempt_number = (
            last_attempt.attempt_number + 1
            if last_attempt
            else 1
        )

        return PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=attempt_number,
            provider=provider,
            idempotency_key=idempotency_key,
            amount=payment.amount,
            currency=payment.currency,
            status=PaymentAttempt.Status.INITIATED,
        )

    @staticmethod
    @transaction.atomic
    def mark_processing(
        *,
        attempt,
    ):
        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .select_related("payment")
            .get(id=attempt.id)
        )

        if attempt.status not in (
            PaymentAttempt.Status.INITIATED,
            PaymentAttempt.Status.REDIRECT_REQUIRED,
        ):
            raise ValidationError(
                "Attempt cannot move to processing."
            )

        attempt.status = PaymentAttempt.Status.PROCESSING
        attempt.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        payment = (
            Payment.objects
            .select_for_update()
            .get(id=attempt.payment_id)
        )

        if payment.status != Payment.Status.SUCCEEDED:
            payment.status = Payment.Status.PROCESSING

            payment.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return attempt

    @staticmethod
    @transaction.atomic
    def mark_failed(
        *,
        attempt,
        failure_code="",
        failure_message="",
    ):
        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .select_related("payment")
            .get(id=attempt.id)
        )

        if attempt.status == PaymentAttempt.Status.SUCCEEDED:
            raise ValidationError(
                "A successful attempt cannot be marked as failed."
            )

        attempt.status = PaymentAttempt.Status.FAILED
        attempt.failure_code = failure_code
        attempt.failure_message = failure_message

        attempt.save(
            update_fields=[
                "status",
                "failure_code",
                "failure_message",
                "updated_at",
            ]
        )

        payment = Payment.objects.select_for_update().get(
            id=attempt.payment_id,
        )

        if payment.status != Payment.Status.SUCCEEDED:
            payment.status = Payment.Status.FAILED

            payment.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return attempt

    @staticmethod
    @transaction.atomic
    def mark_success(
        *,
        attempt,
        provider_transaction_id,
        provider_response=None,
    ):
        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .select_related("payment")
            .get(id=attempt.id)
        )

        payment = (
            Payment.objects
            .select_for_update()
            .get(id=attempt.payment_id)
        )

        if payment.status == Payment.Status.SUCCEEDED:
            return payment

        if attempt.status == PaymentAttempt.Status.FAILED:
            raise ValidationError(
                "A failed attempt cannot succeed."
            )

        if attempt.amount != payment.amount:
            raise ValidationError(
                "Attempt amount does not match payment amount."
            )

        if attempt.currency != payment.currency:
            raise ValidationError(
                "Attempt currency does not match payment currency."
            )

        if attempt.status == PaymentAttempt.Status.SUCCEEDED:
            transaction_exists = (
                PaymentTransaction.objects.filter(
                    payment=payment,
                    transaction_type=PaymentTransaction.Type.CAPTURE,
                    status=PaymentTransaction.Status.SUCCEEDED,
                ).exists()
            )

            if transaction_exists:
                return payment

        attempt.status = PaymentAttempt.Status.SUCCEEDED
        attempt.provider_response = provider_response or {}

        attempt.save(
            update_fields=[
                "status",
                "provider_response",
                "updated_at",
            ]
        )

        PaymentTransaction.objects.create(
            payment=payment,
            attempt=attempt,
            transaction_type=PaymentTransaction.Type.CAPTURE,
            amount=payment.amount,
            currency=payment.currency,
            status=PaymentTransaction.Status.SUCCEEDED,
            provider_transaction_id=provider_transaction_id,
            metadata=provider_response or {},
        )

        reservations = (
            Reservation.objects
            .select_for_update()
            .select_related(
                "inventory",
                "inventory__variant",
            )
            .filter(
                order=payment.order,
                status=Reservation.Status.ACTIVE,
            )
            .order_by("id")
        )

        reservations = list(reservations)

        if not reservations:
            raise ValidationError(
                "Payment cannot succeed without active reservations."
            )

        for reservation in reservations:
            ReservationService.confirm_reservation(
                reservation=reservation,
            )

        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = timezone.now()

        payment.save(
            update_fields=[
                "status",
                "paid_at",
                "updated_at",
            ]
        )

        order = Order.objects.get(
            id=payment.order_id,
        )

        OrderService.confirm_order(
            order=order,
        )

        return payment