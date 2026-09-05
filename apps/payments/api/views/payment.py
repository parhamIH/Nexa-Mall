from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.payments.api.serializers import (
    PaymentAttemptCreateSerializer,
    PaymentAttemptSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
)
from apps.payments.gateways import get_payment_gateway
from apps.payments.selectors.payment import PaymentSelector
from apps.payments.services import PaymentService


class PaymentCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        serializer = PaymentCreateSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        order_id = serializer.validated_data[
            "order_id"
        ]

        order = (
            Order.objects
            .filter(
                id=order_id,
                user=request.user,
            )
            .first()
        )

        if order is None:
            return Response(
                {
                    "detail": "Order not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = PaymentService.create_payment(
                order=order,
                user=request.user,
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                exc.messages,
            )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentDetailView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, payment_id):
        payment = PaymentSelector.user_payment(
            user=request.user,
            payment_id=payment_id,
        )

        if payment is None:
            return Response(
                {
                    "detail": "Payment not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_200_OK,
        )


class PaymentAttemptCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, payment_id):
        payment = PaymentSelector.user_payment(
            user=request.user,
            payment_id=payment_id,
        )

        if payment is None:
            return Response(
                {
                    "detail": "Payment not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PaymentAttemptCreateSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        provider = serializer.validated_data[
            "provider"
        ]

        try:
            gateway = get_payment_gateway(
                provider=provider,
            )

            attempt = PaymentService.initiate_attempt(
                payment=payment,
                provider=provider,
                idempotency_key=serializer.validated_data[
                    "idempotency_key"
                ],
                gateway=gateway,
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                exc.messages,
            )

        return Response(
            PaymentAttemptSerializer(attempt).data,
            status=status.HTTP_201_CREATED,
        )