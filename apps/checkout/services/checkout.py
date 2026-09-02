from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.cart.models import Cart
from apps.cart.services import CartService
from apps.inventory.models import InventoryItem
from apps.inventory.services.reservation import ReservationService
from apps.orders.services import OrderItemService, OrderService


class CheckoutService:

    DEFAULT_RESERVATION_MINUTES = 15

    @staticmethod
    @transaction.atomic
    def start_checkout(
        *,
        cart_id,
        user,
        currency="IRR",
        shipping_address=None,
        billing_address=None,
        customer_note="",
        shipping_cost=0,
        reservation_minutes=None,
    ):
        cart = (
            Cart.objects
            .select_for_update()
            .select_related("shop")
            .get(
                id=cart_id,
                user=user,
            )
        )

        if cart.status != Cart.Status.ACTIVE:
            raise ValidationError(
                "Only active carts can be checked out."
            )

        items = list(
            cart.items
            .select_for_update()
            .select_related(
                "variant",
                "variant__product",
            )
            .order_by("variant_id")
        )

        if not items:
            raise ValidationError(
                "Cannot checkout an empty cart."
            )

        CheckoutService._validate_items(
            cart=cart,
            items=items,
        )

        order = OrderService.create_order(
            shop=cart.shop,
            user=user,
            currency=currency,
            shipping_address=shipping_address,
            billing_address=billing_address,
            customer_note=customer_note,
        )

        order_items = []

        for cart_item in items:
            order_item = OrderItemService.add_item(
                order=order,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
            )

            order_items.append(order_item)

        OrderService.calculate_totals(
            order=order,
            shipping_cost=shipping_cost,
        )

        if reservation_minutes is None:
            reservation_minutes = (
                CheckoutService.DEFAULT_RESERVATION_MINUTES
            )

        if reservation_minutes <= 0:
            raise ValidationError(
                "Reservation duration must be greater than zero."
            )

        expires_at = (
            timezone.now()
            + timedelta(minutes=reservation_minutes)
        )

        for order_item in sorted(
            order_items,
            key=lambda item: str(item.variant_id),
        ):
            ReservationService.create_reservation(
                variant=order_item.variant,
                quantity=order_item.quantity,
                reference=(
                    f"{order.order_number}:"
                    f"{order_item.id}"
                ),
                expires_at=expires_at,
            )

        OrderService.move_to_payment_pending(
            order=order,
        )

        CartService.mark_converted(
            cart=cart,
        )

        return order

    @staticmethod
    def _validate_items(
        *,
        cart,
        items,
    ):
        for cart_item in items:
            variant = cart_item.variant
            product = variant.product

            if product.shop_id != cart.shop_id:
                raise ValidationError(
                    "Cart contains a variant from another shop."
                )

            if product.status != product.Status.ACTIVE:
                raise ValidationError(
                    f"Product '{product.name}' is not active."
                )

            if variant.status != variant.Status.ACTIVE:
                raise ValidationError(
                    f"Variant '{variant.sku}' is not active."
                )

            try:
                InventoryItem.objects.get(
                    variant=variant,
                )

            except InventoryItem.DoesNotExist:
                raise ValidationError(
                    f"Variant '{variant.sku}' has no inventory."
                )