import uuid

from django.db import models

from apps.tenants.models import Tenant
from apps.mall.models.unit import Unit


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