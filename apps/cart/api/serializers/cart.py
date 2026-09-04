from rest_framework import serializers

from apps.cart.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):

    variant_id = serializers.UUIDField(
        source="variant.id",
        read_only=True,
    )

    sku = serializers.CharField(
        source="variant.sku",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="variant.product.name",
        read_only=True,
    )

    variant_name = serializers.CharField(
        source="variant.name",
        read_only=True,
    )

    unit_price = serializers.DecimalField(
        source="variant.price",
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "variant_id",
            "sku",
            "product_name",
            "variant_name",
            "unit_price",
            "quantity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "variant_id",
            "sku",
            "product_name",
            "variant_name",
            "unit_price",
            "quantity",
            "created_at",
            "updated_at",
        ]


class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Cart
        fields = [
            "id",
            "shop",
            "status",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AddCartItemSerializer(serializers.Serializer):

    variant_id = serializers.UUIDField()

    quantity = serializers.IntegerField(
        min_value=1,
    )


class SetCartItemQuantitySerializer(serializers.Serializer):

    quantity = serializers.IntegerField(
        min_value=1,
    )