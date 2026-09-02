import uuid

from django.core.validators import MinValueValidator
from django.db import models


class PaymentTransaction(models.Model):

    class Type(models.TextChoices):
        CAPTURE = "CAPTURE", "Capture"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    attempt = models.ForeignKey(
        "payments.PaymentAttempt",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    currency = models.CharField(
        max_length=3,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )

    provider_transaction_id = models.CharField(
        max_length=255,
        unique=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["payment", "transaction_type"],
            ),
            models.Index(
                fields=["payment", "status"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.payment_id} - "
            f"{self.transaction_type} - "
            f"{self.status}"
        )