from apps.orders.models import Order


class CheckoutSelector:

    @staticmethod
    def get_user_order(
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
