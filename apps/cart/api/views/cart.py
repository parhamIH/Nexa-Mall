from django.core.exceptions import ValidationError
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.responses import success_response
from apps.cart.api.serializers import (
    AddCartItemSerializer,
    CartItemResponseSerializer,
    CartItemSerializer,
    CartResponseSerializer,
    CartSerializer,
    SetCartItemQuantitySerializer,
)
from apps.cart.selectors.cart import CartSelector
from apps.cart.services import CartItemService, CartService


class CartView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        responses={
            200: CartResponseSerializer,
            404: OpenApiResponse(
                description="Active cart does not exist.",
            ),
        },
    )
    def get(self, request, shop_id):
        cart = CartSelector.get_active_cart(
            user=request.user,
            shop_id=shop_id,
        )

        if cart is None:
            raise NotFound(
                "Active cart does not exist."
            )

        return success_response(
            data=CartSerializer(cart).data,
        )


class CartItemCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        request=AddCartItemSerializer,
        responses={
            201: CartItemResponseSerializer,
        },
    )
    def post(self, request, shop_id):
        serializer = AddCartItemSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        shop = CartSelector.get_shop(
            shop_id=shop_id,
        )

        if shop is None:
            raise NotFound(
                "Shop not found."
            )

        variant = CartSelector.get_variant(
            variant_id=serializer.validated_data["variant_id"],
        )

        if variant is None:
            raise NotFound(
                "Variant not found."
            )

        cart = CartService.get_or_create_cart(
            user=request.user,
            shop=shop,
        )

        try:
            item = CartItemService.add_item(
                cart=cart,
                variant=variant,
                quantity=serializer.validated_data["quantity"],
            )
        except ValidationError as exc:
            raise DRFValidationError(
                exc.message,
            )

        return success_response(
            data=CartItemSerializer(item).data,
            status_code=status.HTTP_201_CREATED,
        )


class CartItemDetailView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    @extend_schema(
        request=SetCartItemQuantitySerializer,
        responses=CartItemResponseSerializer,
    )
    def patch(self, request, item_id):
        item = CartSelector.get_item_for_user(
            user=request.user,
            item_id=item_id,
        )

        if item is None:
            raise NotFound(
                "Cart item not found."
            )

        serializer = SetCartItemQuantitySerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            item = CartItemService.set_quantity(
                item=item,
                quantity=serializer.validated_data["quantity"],
                user=request.user,
            )
        except ValidationError as exc:
            raise DRFValidationError(
                exc.message,
            )

        return success_response(
            data=CartItemSerializer(item).data,
        )

    @extend_schema(
        responses={
            204: OpenApiResponse(
                description="Cart item removed.",
            ),
        },
    )
    def delete(self, request, item_id):
        item = CartSelector.get_item_for_user(
            user=request.user,
            item_id=item_id,
        )

        if item is None:
            raise NotFound(
                "Cart item not found."
            )

        try:
            CartItemService.remove_item(
                item=item,
                user=request.user,
            )
        except ValidationError as exc:
            raise DRFValidationError(
                exc.message,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )