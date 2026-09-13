from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models.functions import Upper
import uuid


class Brand(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    logo = models.ImageField(
        upload_to="catalog/brands/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            # Functional trigram GIN on Upper(name): Django's
            # icontains compiles to UPPER(col) LIKE '%..%'.
            GinIndex(
                OpClass(Upper("name"), name="gin_trgm_ops"),
                name="brand_name_trgm_idx",
            ),
        ]

    def __str__(self):
        return self.name

