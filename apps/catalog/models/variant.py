from django.db import models

import uuid
from django.core.validators import MinValueValidator


class ProductVariant(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "Inactive"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="variants",
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
    )

    name = models.CharField(
        max_length=200,
        blank=True,
    )

    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    compare_at_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    weight_grams = models.PositiveIntegerField(
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    option_values = models.ManyToManyField(
        "catalog.ProductOptionValue",
        through="ProductVariantOptionValue",
        related_name="variants",
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
                fields=["product", "status"],
            ),
        ]

    def __str__(self):
        return self.name or self.sku




class ProductVariantOptionValue(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="variant_option_values",
    )

    option_value = models.ForeignKey(
        "catalog.ProductOptionValue",
        on_delete=models.CASCADE,
        related_name="variant_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "option_value"],
                name="unique_variant_option_value",
            )
        ]

    def __str__(self):
        return f"{self.variant.sku} - {self.option_value.value}"