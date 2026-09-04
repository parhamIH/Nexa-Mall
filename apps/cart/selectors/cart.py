from django.db.models import QuerySet

from apps.cart.models import Cart, CartItem
from apps.catalog.models import ProductVariant
from apps.tenants.models import Shop


class CartSelector:

    @staticmethod
    def get_active_cart(
        *,
        user,
        shop_id,
    ):
        return (
            Cart.objects
            .filter(
                user=user,
                shop_id=shop_id,
                status=Cart.Status.ACTIVE,
            )
            .select_related("shop")
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
            .order_by("-updated_at", "id")
        )

    @staticmethod
    def get_item_for_user(
        *,
        user,
        item_id,
    ):
        return (
            CartItem.objects
            .filter(
                id=item_id,
                cart__user=user,
            )
            .select_related(
                "cart",
                "cart__shop",
                "variant",
                "variant__product",
            )
            .first()
        )

    @staticmethod
    def get_shop(
        *,
        shop_id,
    ):
        return (
            Shop.objects
            .select_related("tenant")
            .filter(id=shop_id)
            .first()
        )

    @staticmethod
    def get_variant(
        *,
        variant_id,
    ):
        return (
            ProductVariant.objects
            .select_related("product", "product__shop")
            .filter(id=variant_id)
            .first()
        )