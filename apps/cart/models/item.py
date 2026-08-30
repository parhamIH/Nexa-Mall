import uuid

from django.core.validators import MinValueValidator
from django.db import models


class CartItem(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    cart = models.ForeignKey(
        "cart.Cart",
        on_delete=models.CASCADE,
        related_name="items",
    )

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
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
                fields=["cart", "variant"],
                name="unique_variant_per_cart",
            ),
        ]

        indexes = [
            models.Index(
                fields=["cart"],
            ),
            models.Index(
                fields=["variant"],
            ),
        ]

    def __str__(self):
        return f"{self.variant.sku} × {self.quantity}"