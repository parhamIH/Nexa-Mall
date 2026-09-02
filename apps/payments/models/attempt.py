import uuid

from django.core.validators import MinValueValidator
from django.db import models


class PaymentAttempt(models.Model):

    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        REDIRECT_REQUIRED = "REDIRECT_REQUIRED", "Redirect required"
        PROCESSING = "PROCESSING", "Processing"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="attempts",
    )

    attempt_number = models.PositiveIntegerField()

    provider = models.CharField(
        max_length=50,
    )

    idempotency_key = models.CharField(
        max_length=100,
        unique=True,
    )

    provider_reference = models.CharField(
        max_length=255,
        blank=True,
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
        max_length=30,
        choices=Status.choices,
        default=Status.INITIATED,
    )

    failure_code = models.CharField(
        max_length=100,
        blank=True,
    )

    failure_message = models.TextField(
        blank=True,
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "attempt_number"],
                name="unique_payment_attempt_number",
            ),
        ]

        indexes = [
            models.Index(
                fields=["payment", "status"],
            ),
            models.Index(
                fields=["provider", "provider_reference"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.payment_id} - "
            f"Attempt #{self.attempt_number} - "
            f"{self.status}"
        )