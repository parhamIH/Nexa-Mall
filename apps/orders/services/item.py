from django.core.exceptions import ValidationError
from django.db import transaction

from apps.orders.models import Order, OrderItem


class OrderItemService:

    @staticmethod
    @transaction.atomic
    def add_item(
        *,
        order,
        variant,
        quantity,
    ):
        if order.status != Order.Status.PENDING:
            raise ValidationError(
                "Items can only be added to pending orders."
            )

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if variant.product.shop_id != order.shop_id:
            raise ValidationError(
                "Variant does not belong to the order shop."
            )

        unit_price = variant.price
        total_price = unit_price * quantity

        return OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name,
            variant_name=variant.name,
            sku=variant.sku,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
        )