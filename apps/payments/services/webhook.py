from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.payments.gateways import PaymentGateway
from apps.payments.models import (
    PaymentAttempt,
    WebhookEvent,
)
from apps.payments.services.payment import PaymentService


class WebhookService:

    @staticmethod
    @transaction.atomic
    def process(
        *,
        provider,
        event_id,
        event_type,
        payload,
        gateway: PaymentGateway,
        signature=None,
    ):
        # -------------------------------------------------
        # 1. Verify webhook authenticity
        # -------------------------------------------------

        gateway.verify_webhook(
            payload=payload,
            signature=signature,
        )

        # -------------------------------------------------
        # 2. Idempotency
        # -------------------------------------------------

        webhook_event, created = WebhookEvent.objects.get_or_create(
            provider=provider,
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload": payload,
                "status": WebhookEvent.Status.RECEIVED,
            },
        )

        if not created:
            if webhook_event.status == WebhookEvent.Status.PROCESSED:
                return webhook_event

            if webhook_event.status == WebhookEvent.Status.IGNORED:
                return webhook_event

        # -------------------------------------------------
        # 3. Find payment attempt
        # -------------------------------------------------

        provider_reference = payload.get(
            "provider_reference",
        )

        if not provider_reference:
            webhook_event.status = WebhookEvent.Status.IGNORED
            webhook_event.processed_at = timezone.now()

            webhook_event.save(
                update_fields=[
                    "status",
                    "processed_at",
                ]
            )

            return webhook_event

        attempt = (
            PaymentAttempt.objects
            .select_for_update()
            .select_related("payment")
            .filter(
                provider=provider,
                provider_reference=provider_reference,
            )
            .first()
        )

        if not attempt:
            webhook_event.status = WebhookEvent.Status.IGNORED
            webhook_event.processed_at = timezone.now()

            webhook_event.save(
                update_fields=[
                    "status",
                    "processed_at",
                ]
            )

            return webhook_event

        # -------------------------------------------------
        # 4. Verify payment with provider
        # -------------------------------------------------

        result = gateway.verify_payment(
            attempt=attempt,
            payload=payload,
        )

        # -------------------------------------------------
        # 5. Payment failed
        # -------------------------------------------------

        if not result.success:
            PaymentService.mark_failed(
                attempt=attempt,
                failure_code=result.failure_code,
                failure_message=result.failure_message,
            )

            webhook_event.status = WebhookEvent.Status.PROCESSED
            webhook_event.processed_at = timezone.now()

            webhook_event.save(
                update_fields=[
                    "status",
                    "processed_at",
                ]
            )

            return webhook_event

        # -------------------------------------------------
        # 6. Payment succeeded
        # -------------------------------------------------

        if not result.provider_transaction_id:
            raise ValidationError(
                "Successful payment must contain "
                "a provider transaction ID."
            )

        PaymentService.mark_success(
            attempt=attempt,
            provider_transaction_id=result.provider_transaction_id,
            provider_response=result.raw_response,
        )

        webhook_event.status = WebhookEvent.Status.PROCESSED
        webhook_event.processed_at = timezone.now()

        webhook_event.save(
            update_fields=[
                "status",
                "processed_at",
            ]
        )

        return webhook_event