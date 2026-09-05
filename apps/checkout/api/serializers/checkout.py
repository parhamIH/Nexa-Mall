from rest_framework import serializers

from apps.orders.models import Order, OrderItem


class CheckoutCreateSerializer(serializers.Serializer):

    cart_id = serializers.UUIDField()

    currency = serializers.CharField(
        max_length=3,
        default="IRR",
    )

    shipping_address = serializers.JSONField(
        required=False,
        default=dict,
    )

    billing_address = serializers.JSONField(
        required=False,
        default=dict,
    )

    customer_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    shipping_cost = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
        required=False,
        default=0,
    )

    reservation_minutes = serializers.IntegerField(
        min_value=1,
        required=False,
        default=15,
    )


class CheckoutOrderItemSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = OrderItem

        fields = [
            "id",
            "product_name",
            "variant_name",
            "sku",
            "quantity",
            "unit_price",
            "total_price",
        ]

        read_only_fields = fields


class CheckoutOrderSerializer(
    serializers.ModelSerializer,
):
    items = CheckoutOrderItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Order

        fields = [
            "id",
            "order_number",
            "shop",
            "status",
            "currency",
            "subtotal",
            "discount",
            "shipping_cost",
            "total",
            "shipping_address",
            "billing_address",
            "customer_note",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
