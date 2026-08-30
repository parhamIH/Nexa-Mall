from django.db import transaction

from apps.orders.models import Order


class OrderService:

    @staticmethod
    @transaction.atomic
    def create_order(
        *,
        shop,
        user,
        currency="IRR",
    ):
        return Order.objects.create(
            shop=shop,
            user=user,
            status=Order.Status.PENDING,
            currency=currency,
            subtotal=0,
            discount=0,
            shipping_cost=0,
            total=0,
        )