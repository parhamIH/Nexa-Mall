import uuid

from django.core.validators import MinValueValidator
from django.db import models


class OrderItem(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items",
    )

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    product_name = models.CharField(
        max_length=200,
    )

    variant_name = models.CharField(
        max_length=200,
        blank=True,
    )

    sku = models.CharField(
        max_length=100,
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    total_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["order"],
            ),
            models.Index(
                fields=["variant"],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["order", "variant"],
                name="unique_variant_per_order",
            ),
        ]

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"