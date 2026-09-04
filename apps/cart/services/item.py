from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.cart.models import Cart, CartItem


class CartItemService:

    @staticmethod
    def _require_cart_ownership(
        *,
        item,
        user,
    ):
        if item.cart.user_id != user.id:
            raise PermissionDenied(
                "You do not own this cart."
            )

    @staticmethod
    @transaction.atomic
    def add_item(
        *,
        cart,
        variant,
        quantity,
    ):
        if cart.status != Cart.Status.ACTIVE:
            raise ValidationError(
                "Cannot modify an inactive cart."
            )

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if variant.product.shop_id != cart.shop_id:
            raise ValidationError(
                "Variant does not belong to this shop."
            )

        item, created = (
            CartItem.objects
            .select_for_update()
            .get_or_create(
                cart=cart,
                variant=variant,
                defaults={
                    "quantity": quantity,
                },
            )
        )

        if not created:
            item.quantity += quantity

            item.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ]
            )

        return item

    @staticmethod
    @transaction.atomic
    def set_quantity(
        *,
        item,
        quantity,
        user,
    ):
        CartItemService._require_cart_ownership(
            item=item,
            user=user,
        )

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if item.cart.status != Cart.Status.ACTIVE:
            raise ValidationError(
                "Cannot modify an inactive cart."
            )

        item.quantity = quantity

        item.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        return item

    @staticmethod
    @transaction.atomic
    def remove_item(
        *,
        item,
        user,
    ):
        CartItemService._require_cart_ownership(
            item=item,
            user=user,
        )

        if item.cart.status != Cart.Status.ACTIVE:
            raise ValidationError(
                "Cannot modify an inactive cart."
            )

        item.delete()