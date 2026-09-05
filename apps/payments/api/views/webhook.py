from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.throttling import WebhookRateThrottle
from apps.payments.api.serializers import WebhookSerializer
from apps.payments.gateways import get_payment_gateway
from apps.payments.services.webhook import WebhookService


class PaymentWebhookView(APIView):

    permission_classes = [
        AllowAny,
    ]

    authentication_classes = []

    throttle_classes = [
        WebhookRateThrottle,
    ]

    def post(self, request, provider):
        serializer = WebhookSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        signature = request.headers.get(
            "X-Webhook-Signature",
        )

        data = serializer.validated_data

        try:
            gateway = get_payment_gateway(
                provider=provider,
            )

            event = WebhookService.process(
                provider=provider,
                event_id=data["event_id"],
                event_type=data["event_type"],
                payload=data["payload"],
                gateway=gateway,
                signature=signature,
            )

        except DjangoValidationError as exc:
            return Response(
                {
                    "detail": exc.messages,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "event_id": event.event_id,
                "status": event.status,
            },
            status=status.HTTP_200_OK,
        )