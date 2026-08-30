from django.db.models import QuerySet

from apps.cart.models import Cart


class CartSelector:

    @staticmethod
    def get_active_cart(
        *,
        user,
        shop,
    ) -> Cart:
        return (
            Cart.objects
            .filter(
                user=user,
                shop=shop,
                status=Cart.Status.ACTIVE,
            )
            .prefetch_related(
                "items__variant__product",
            )
            .first()
        )

    @staticmethod
    def get_user_carts(
        *,
        user,
    ) -> QuerySet:
        return (
            Cart.objects
            .filter(user=user)
            .select_related("shop")
            .prefetch_related(
                "items__variant__product",
            )
        )