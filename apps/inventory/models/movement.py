import uuid

from django.core.validators import MinValueValidator
from django.db import models


class StockMovement(models.Model):

    class Type(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        SALE = "SALE", "Sale"
        RETURN = "RETURN", "Return"
        DAMAGE = "DAMAGE", "Damage"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    inventory = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    reference = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.inventory.variant.sku} - "
            f"{self.movement_type} - "
            f"{self.quantity}"
        )