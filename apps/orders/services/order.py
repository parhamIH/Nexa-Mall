from decimal import Decimal

from django.core.exceptions import ValidationError
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
        shipping_address=None,
        billing_address=None,
        customer_note="",
    ):
        return Order.objects.create(
            shop=shop,
            user=user,
            status=Order.Status.PENDING,
            currency=currency,
            subtotal=Decimal("0"),
            discount=Decimal("0"),
            shipping_cost=Decimal("0"),
            total=Decimal("0"),
            shipping_address=shipping_address or {},
            billing_address=billing_address or {},
            customer_note=customer_note,
        )

    @staticmethod
    @transaction.atomic
    def calculate_totals(
        *,
        order,
        discount=None,
        shipping_cost=None,
    ):
        subtotal = sum(
            (
                item.total_price
                for item in order.items.all()
            ),
            Decimal("0"),
        )

        if discount is not None:
            discount = Decimal(discount)

        else:
            discount = order.discount

        if shipping_cost is not None:
            shipping_cost = Decimal(shipping_cost)

        else:
            shipping_cost = order.shipping_cost

        if discount < 0:
            raise ValidationError(
                "Discount cannot be negative."
            )

        if shipping_cost < 0:
            raise ValidationError(
                "Shipping cost cannot be negative."
            )

        if discount > subtotal:
            raise ValidationError(
                "Discount cannot exceed subtotal."
            )

        total = (
            subtotal
            - discount
            + shipping_cost
        )

        order.subtotal = subtotal
        order.discount = discount
        order.shipping_cost = shipping_cost
        order.total = total

        order.save(
            update_fields=[
                "subtotal",
                "discount",
                "shipping_cost",
                "total",
                "updated_at",
            ]
        )

        return order

    @staticmethod
    @transaction.atomic
    def move_to_payment_pending(
        *,
        order,
    ):
        if order.status != Order.Status.PENDING:
            raise ValidationError(
                "Only pending orders can enter payment pending."
            )

        if not order.items.exists():
            raise ValidationError(
                "An order must have at least one item."
            )

        order.status = Order.Status.PAYMENT_PENDING

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    
    @staticmethod
    @transaction.atomic
    def confirm_order(
        *,
        order,
    ):
        if order.status != Order.Status.PAYMENT_PENDING:
            raise ValidationError(
                "Only payment-pending orders can be confirmed."
            )

        order.status = Order.Status.CONFIRMED

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return order
        return order