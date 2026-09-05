from apps.payments.models import Payment, PaymentAttempt


class PaymentSelector:

    @staticmethod
    def user_payment(
        *,
        user,
        payment_id,
    ):
        return (
            Payment.objects
            .filter(
                id=payment_id,
                user=user,
            )
            .select_related(
                "order",
                "order__shop",
            )
            .prefetch_related(
                "attempts",
                "transactions",
            )
            .first()
        )

    @staticmethod
    def user_payment_for_order(
        *,
        user,
        order_id,
    ):
        return (
            Payment.objects
            .filter(
                order_id=order_id,
                user=user,
            )
            .select_related(
                "order",
                "order__shop",
            )
            .prefetch_related(
                "attempts",
                "transactions",
            )
            .first()
        )

    @staticmethod
    def payment_attempt(
        *,
        user,
        attempt_id,
    ):
        return (
            PaymentAttempt.objects
            .filter(
                id=attempt_id,
                payment__user=user,
            )
            .select_related(
                "payment",
            )
            .first()
        )
