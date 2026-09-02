import uuid

from django.db import models


class WebhookEvent(models.Model):

    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        PROCESSED = "PROCESSED", "Processed"
        IGNORED = "IGNORED", "Ignored"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    provider = models.CharField(
        max_length=50,
    )

    event_id = models.CharField(
        max_length=255,
    )

    event_type = models.CharField(
        max_length=100,
    )

    payload = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"],
                name="unique_provider_webhook_event",
            ),
        ]

        indexes = [
            models.Index(
                fields=["provider", "event_type"],
            ),
            models.Index(
                fields=["status", "created_at"],
            ),
        ]

    def __str__(self):
        return f"{self.provider} - {self.event_id}"