from django.db import transaction
from django.core.exceptions import ValidationError

from apps.cart.models import CartItem


class CartItemService:

    @staticmethod
    @transaction.atomic
    def add_item(
        *,
        cart,
        variant,
        quantity,
    ):
        if cart.status != cart.Status.ACTIVE:
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
    ):
        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if item.cart.status != item.cart.Status.ACTIVE:
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
    ):
        if item.cart.status != item.cart.Status.ACTIVE:
            raise ValidationError(
                "Cannot modify an inactive cart."
            )

        item.delete()