import uuid

from django.conf import settings
from django.db import models


class Cart(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CONVERTED = "CONVERTED", "Converted"
        ABANDONED = "ABANDONED", "Abandoned"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
    )

    shop = models.ForeignKey(
        "tenants.Shop",
        on_delete=models.PROTECT,
        related_name="carts",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
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
                fields=["user", "shop"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_cart_per_user_shop",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "status"],
            ),
            models.Index(
                fields=["shop", "status"],
            ),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.shop_id} - {self.status}"