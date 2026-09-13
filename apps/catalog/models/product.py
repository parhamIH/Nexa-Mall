from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models.functions import Upper
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
            # Trigram GIN indexes for substring search. IMPORTANT:
            # Django's icontains compiles to UPPER(col) LIKE '%..%'
            # (NOT ILIKE), so the index must be a FUNCTIONAL index on
            # Upper(col) - a plain column index can never match the
            # query's UPPER(...) predicate. A leading-wildcard LIKE
            # cannot use B-tree; pg_trgm turns it into a trigram
            # bitmap index scan. PostgreSQL-only.
            GinIndex(
                OpClass(Upper("name"), name="gin_trgm_ops"),
                name="product_name_trgm_idx",
            ),
            GinIndex(
                OpClass(Upper("slug"), name="gin_trgm_ops"),
                name="product_slug_trgm_idx",
            ),
            GinIndex(
                OpClass(Upper("description"), name="gin_trgm_ops"),
                name="product_desc_trgm_idx",
            ),
        ]

    def __str__(self):
        return self.name

