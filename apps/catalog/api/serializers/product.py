from rest_framework import serializers

from apps.catalog.models import Product, ProductVariant


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


class ProductVariantDetailSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = ProductVariant

        fields = [
            "id",
            "sku",
            "name",
            "price",
            "compare_at_price",
            "weight_grams",
            "status",
        ]

        read_only_fields = fields


class ProductDetailSerializer(
    serializers.ModelSerializer,
):
    brand_name = serializers.CharField(
        source="brand.name",
        read_only=True,
        allow_null=True,
    )

    category_ids = serializers.PrimaryKeyRelatedField(
        source="categories",
        many=True,
        read_only=True,
    )

    variants = ProductVariantDetailSerializer(
        many=True,
        read_only=True,
    )

    variant_count = serializers.SerializerMethodField()

    min_variant_price = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "brand_name",
            "category_ids",
            "status",
            "variants",
            "variant_count",
            "min_variant_price",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    # SerializerMethodFields are part of the representation cost:
    # they must consume prefetched relations only - never trigger
    # queries per field (N+1).

    def get_variant_count(
        self,
        obj,
    ) -> int:
        return len(obj.variants.all())

    def get_min_variant_price(
        self,
        obj,
    ):
        prices = [
            variant.price
            for variant in obj.variants.all()
        ]

        if not prices:
            return None

        return min(prices)