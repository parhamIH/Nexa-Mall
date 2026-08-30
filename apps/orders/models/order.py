import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


def generate_order_number():
    return f"NM-{uuid.uuid4().hex[:12].upper()}"


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment pending"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order_number = models.CharField(
        max_length=20,
        unique=True,
        default=generate_order_number,
        editable=False,
    )

    shop = models.ForeignKey(
        "tenants.Shop",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    currency = models.CharField(
        max_length=3,
        default="IRR",
    )

    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    discount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    shipping_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    shipping_address = models.JSONField(
        default=dict,
        blank=True,
    )

    billing_address = models.JSONField(
        default=dict,
        blank=True,
    )

    customer_note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["shop", "status"],
            ),
            models.Index(
                fields=["user", "created_at"],
            ),
            models.Index(
                fields=["status", "created_at"],
            ),
            models.Index(
                fields=["shop", "created_at"],
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    discount__lte=models.F("subtotal"),
                ),
                name="order_discount_lte_subtotal",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    total=(
                        models.F("subtotal")
                        - models.F("discount")
                        + models.F("shipping_cost")
                    ),
                ),
                name="order_total_matches_components",
            ),
        ]

    def __str__(self):
        return self.order_number