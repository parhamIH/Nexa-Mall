from rest_framework import serializers

from apps.payments.models import (
    Payment,
    PaymentAttempt,
    PaymentTransaction,
)


class PaymentTransactionSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = PaymentTransaction

        fields = [
            "id",
            "transaction_type",
            "amount",
            "currency",
            "status",
            "provider_transaction_id",
            "metadata",
            "created_at",
        ]

        read_only_fields = fields


class PaymentAttemptSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = PaymentAttempt

        fields = [
            "id",
            "attempt_number",
            "provider",
            "provider_reference",
            "amount",
            "currency",
            "status",
            "failure_code",
            "failure_message",
            "provider_response",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class PaymentSerializer(
    serializers.ModelSerializer,
):
    attempts = PaymentAttemptSerializer(
        many=True,
        read_only=True,
    )

    transactions = PaymentTransactionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Payment

        fields = [
            "id",
            "order",
            "amount",
            "currency",
            "status",
            "paid_at",
            "attempts",
            "transactions",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class PaymentCreateSerializer(
    serializers.Serializer,
):
    order_id = serializers.UUIDField()


class PaymentAttemptCreateSerializer(
    serializers.Serializer,
):
    provider = serializers.CharField(
        max_length=50,
    )

    idempotency_key = serializers.CharField(
        max_length=100,
    )