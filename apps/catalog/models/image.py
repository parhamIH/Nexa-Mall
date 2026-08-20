import uuid

from django.db import models


class ProductImage(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="catalog/products/",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    position = models.PositiveIntegerField(
        default=0,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["position", "created_at"]

        indexes = [
            models.Index(
                fields=["product", "position"],
            ),
        ]

    def __str__(self):
        return f"{self.product.name} image"