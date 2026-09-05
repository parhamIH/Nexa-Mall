from django.db.models import QuerySet

from apps.orders.models import Order


class OrderSelector:

    @staticmethod
    def user_orders(
        *,
        user,
    ) -> QuerySet:
        return (
            Order.objects
            .filter(
                user=user,
            )
            .select_related(
                "shop",
            )
            .prefetch_related(
                "items",
            )
            .order_by(
                "-created_at",
                "id",
            )
        )

    @staticmethod
    def user_order(
        *,
        user,
        order_id,
    ):
        return (
            Order.objects
            .filter(
                id=order_id,
                user=user,
            )
            .select_related(
                "shop",
            )
            .prefetch_related(
                "items",
            )
            .first()
        )

    @staticmethod
    def shop_orders(
        *,
        user,
        shop_id,
    ) -> QuerySet:
        return (
            Order.objects
            .filter(
                shop_id=shop_id,
                shop__tenant__memberships__user=user,
                shop__tenant__memberships__is_active=True,
                shop__tenant__memberships__role__in=[
                    "OWNER",
                    "MANAGER",
                ],
            )
            .select_related(
                "shop",
                "user",
            )
            .prefetch_related(
                "items",
            )
            .order_by(
                "-created_at",
                "id",
            )
            .distinct()
        )
