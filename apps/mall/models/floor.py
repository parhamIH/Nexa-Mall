import uuid

from django.db import models

from apps.mall.models.mall import Mall

class Floor(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    mall = models.ForeignKey(
        Mall,
        on_delete=models.CASCADE,
        related_name="floors",
    )

    name = models.CharField(
        max_length=100,
    )

    number = models.IntegerField()

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["number"]

        constraints = [
            models.UniqueConstraint(
                fields=["mall", "number"],
                name="unique_floor_number_per_mall",
            )
        ]

    def __str__(self):
        return f"{self.mall.name} - {self.name}"

