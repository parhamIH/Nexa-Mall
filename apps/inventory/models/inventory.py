import uuid

from django.core.validators import MinValueValidator
from django.db import models


class InventoryItem(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    variant = models.OneToOneField(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="inventory",
    )

    on_hand = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )

    reserved = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    @property
    def available(self):
        return self.on_hand - self.reserved

    def __str__(self):
        return f"{self.variant.sku} - {self.available} available"