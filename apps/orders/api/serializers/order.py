from rest_framework import serializers

from apps.orders.models import Order, OrderItem


class OrderItemSerializer(
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


class OrderSerializer(
    serializers.ModelSerializer,
):
    items = OrderItemSerializer(
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