import uuid

from django.db import models

from apps.mall.models.floor import Floor


class Unit(models.Model):

    class UnitType(models.TextChoices):
        SHOP = "SHOP", "Shop"
        OFFICE = "OFFICE", "Office"
        KIOSK = "KIOSK", "Kiosk"
        STORAGE = "STORAGE", "Storage"
        FOOD_COURT = "FOOD_COURT", "Food Court"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        RESERVED = "RESERVED", "Reserved"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="units",
    )

    code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=150,
        blank=True,
    )

    area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    unit_type = models.CharField(
        max_length=20,
        choices=UnitType.choices,
        default=UnitType.SHOP,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
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
                fields=["floor", "code"],
                name="unique_unit_code_per_floor",
            )
        ]

    def __str__(self):
        return self.code


