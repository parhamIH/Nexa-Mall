from django.db import transaction

from apps.cart.models import Cart


class CartService:

    @staticmethod
    @transaction.atomic
    def get_or_create_cart(
        *,
        user,
        shop,
    ):
        cart, _ = Cart.objects.get_or_create(
            user=user,
            shop=shop,
            status=Cart.Status.ACTIVE,
        )

        return cart

    @staticmethod
    @transaction.atomic
    def abandon_cart(
        *,
        cart,
    ):
        if cart.status != Cart.Status.ACTIVE:
            raise ValueError(
                "Only active carts can be abandoned."
            )

        cart.status = Cart.Status.ABANDONED

        cart.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return cart

    @staticmethod
    @transaction.atomic
    def mark_converted(
        *,
        cart,
    ):
        if cart.status != Cart.Status.ACTIVE:
            raise ValueError(
                "Only active carts can be converted."
            )

        cart.status = Cart.Status.CONVERTED

        cart.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return cart