from django.db import models
import uuid
from ..managers import ProductManager

class Product(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    shop = models.ForeignKey(
        "tenants.Shop",
        on_delete=models.PROTECT,
        related_name="products",
    )

    name = models.CharField(
        max_length=200,
    )

    slug = models.SlugField(
        max_length=220,
    )

    description = models.TextField(
        blank=True,
    )

    brand = models.ForeignKey(
        "catalog.Brand",
        on_delete=models.PROTECT,
        related_name="products",
        blank=True,
        null=True,
    )

    categories = models.ManyToManyField(
        "catalog.Category",
        related_name="products",
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = ProductManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "slug"],
                name="unique_product_slug_per_shop",
            )
        ]

        indexes = [
            models.Index(
                fields=["shop", "status"],
            ),
            models.Index(
                fields=["status", "created_at"],
            ),
        ]

    def __str__(self):
        return self.name

