from rest_framework import serializers

from apps.catalog.models import Product


class ProductListSerializer(serializers.ModelSerializer):
    shop_id = serializers.UUIDField(
        source="shop.id",
        read_only=True,
    )

    brand_name = serializers.CharField(
        source="brand.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "shop_id",
            "name",
            "slug",
            "description",
            "brand_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields



class ProductManagementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "brand",
            "categories",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_status(self, value):
        if value == Product.Status.ARCHIVED:
            return value

        return value


class ProductPaginationMetaSerializer(
    serializers.Serializer,
):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField()

    next = serializers.URLField(
        allow_null=True,
    )

    previous = serializers.URLField(
        allow_null=True,
    )


class ProductListResponseSerializer(
    serializers.Serializer,
):
    data = ProductListSerializer(
        many=True,
    )

    meta = ProductPaginationMetaSerializer()


class ProductDetailResponseSerializer(
    serializers.Serializer,
):
    data = ProductListSerializer()
    meta = serializers.DictField()