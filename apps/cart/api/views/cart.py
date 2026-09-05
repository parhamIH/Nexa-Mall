from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.api.serializers import (
    AddCartItemSerializer,
    CartItemSerializer,
    CartSerializer,
    SetCartItemQuantitySerializer,
)
from apps.cart.selectors.cart import CartSelector
from apps.cart.services import CartItemService, CartService


class CartView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, shop_id):
        cart = CartSelector.get_active_cart(
            user=request.user,
            shop_id=shop_id,
        )

        if cart is None:
            return Response(
                {
                    "detail": "Active cart does not exist.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK,
        )


class CartItemCreateView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

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
            return Response(
                {
                    "detail": "Shop not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        variant = CartSelector.get_variant(
            variant_id=serializer.validated_data["variant_id"],
        )

        if variant is None:
            return Response(
                {
                    "detail": "Variant not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
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
            return Response(
                {
                    "detail": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CartItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class CartItemDetailView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def patch(self, request, item_id):
        item = CartSelector.get_item_for_user(
            user=request.user,
            item_id=item_id,
        )

        if item is None:
            return Response(
                {
                    "detail": "Cart item not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
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
            return Response(
                {
                    "detail": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CartItemSerializer(item).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, item_id):
        item = CartSelector.get_item_for_user(
            user=request.user,
            item_id=item_id,
        )

        if item is None:
            return Response(
                {
                    "detail": "Cart item not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            CartItemService.remove_item(
                item=item,
                user=request.user,
            )
        except ValidationError as exc:
            return Response(
                {
                    "detail": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )