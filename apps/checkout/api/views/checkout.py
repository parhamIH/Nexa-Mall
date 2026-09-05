from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.checkout.api.serializers import (
    CheckoutCreateSerializer,
    CheckoutOrderSerializer,
)
from apps.checkout.services import CheckoutService


class CheckoutCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        serializer = CheckoutCreateSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        data = serializer.validated_data

        try:
            order = CheckoutService.start_checkout(
                cart_id=data["cart_id"],
                user=request.user,
                currency=data["currency"],
                shipping_address=data["shipping_address"],
                billing_address=data["billing_address"],
                customer_note=data["customer_note"],
                shipping_cost=data["shipping_cost"],
                reservation_minutes=data[
                    "reservation_minutes"
                ],
            )

        except Cart.DoesNotExist:
            return Response(
                {
                    "detail": "Cart not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except DjangoValidationError as exc:
            raise ValidationError(
                exc.messages,
            )

        return Response(
            CheckoutOrderSerializer(
                order,
            ).data,
            status=status.HTTP_201_CREATED,
        )
