from apps.payments.gateways.base import (
    PaymentGateway,
    PaymentInitiationResult,
    PaymentVerificationResult,
)


class MockPaymentGateway(PaymentGateway):

    name = "mock"

    def initiate_payment(
        self,
        *,
        payment,
        attempt,
    ):
        return PaymentInitiationResult(
            provider_reference=f"MOCK-{attempt.id}",
            redirect_url=(
                f"https://mock-gateway.local/pay/{attempt.id}"
            ),
        )

    def verify_payment(
        self,
        *,
        attempt,
        payload,
    ):
        status = payload.get("status")

        if status == "success":
            return PaymentVerificationResult(
                success=True,
                provider_transaction_id=payload.get(
                    "transaction_id",
                ),
                raw_response=payload,
            )

        return PaymentVerificationResult(
            success=False,
            failure_code=payload.get(
                "failure_code",
                "PAYMENT_FAILED",
            ),
            failure_message=payload.get(
                "failure_message",
                "Payment failed.",
            ),
            raw_response=payload,
        )

    def verify_webhook(
        self,
        *,
        payload,
        signature=None,
    ):
        # Mock gateway has no real signature verification.
        return None