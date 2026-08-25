import uuid

from django.core.validators import MinValueValidator
from django.db import models


class Reservation(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CONFIRMED = "CONFIRMED", "Confirmed"
        RELEASED = "RELEASED", "Released"
        EXPIRED = "EXPIRED", "Expired"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    inventory = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
    )

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["status", "expires_at"],
            ),
            models.Index(
                fields=["inventory", "status"],
            ),
        ]

    def __str__(self):
        return f"{self.reference} - {self.status}"