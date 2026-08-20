from django.db import models

import uuid
from django.core.validators import MinValueValidator



class ProductOption(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="options",
    )

    name = models.CharField(
        max_length=100,
    )

    code = models.SlugField(
        max_length=100,
    )

    position = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["position"]

        constraints = [
            models.UniqueConstraint(
                fields=["product", "code"],
                name="unique_product_option_code",
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductOptionValue(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    option = models.ForeignKey(
        ProductOption,
        on_delete=models.CASCADE,
        related_name="values",
    )

    value = models.CharField(
        max_length=100,
    )

    code = models.SlugField(
        max_length=100,
    )

    position = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["position"]

        constraints = [
            models.UniqueConstraint(
                fields=["option", "code"],
                name="unique_option_value_code",
            )
        ]

    def __str__(self):
        return self.value


