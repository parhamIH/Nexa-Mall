import uuid

from django.db import models

from apps.tenants.models import Tenant

class Mall(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
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

    def __str__(self):
        return self.name


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



class Contract(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        TERMINATED = "TERMINATED", "Terminated"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="contracts",
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="contracts",
    )

    start_date = models.DateField()

    end_date = models.DateField()

    rent_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    deposit_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
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

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.tenant.name} - {self.unit.code}"