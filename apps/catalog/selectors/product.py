from django.db.models import Prefetch, QuerySet

from catalog.models import (
    Product,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
)


class ProductSelector:

    @staticmethod
    def base_queryset() -> QuerySet:
        return (
            Product.objects
            .select_related("shop", "brand")
            .prefetch_related(
                "categories",
                "images",
                Prefetch(
                    "options",
                    queryset=(
                        ProductOption.objects
                        .order_by("position")
                        .prefetch_related(
                            Prefetch(
                                "values",
                                queryset=ProductOptionValue.objects.order_by(
                                    "position"
                                ),
                            )
                        )
                    ),
                ),
                Prefetch(
                    "variants",
                    queryset=(
                        ProductVariant.objects
                        .filter(
                            status=ProductVariant.Status.ACTIVE
                        )
                        .prefetch_related("option_values")
                    ),
                ),
            )
        )

    @staticmethod
    def get_by_id(
        *,
        product_id,
    ) -> Product:
        return (
            ProductSelector
            .base_queryset()
            .get(id=product_id)
        )

    @staticmethod
    def get_shop_products(
        *,
        shop,
    ) -> QuerySet:
        return (
            ProductSelector
            .base_queryset()
            .filter(shop=shop)
        )

    @staticmethod
    def get_active_products(
        *,
        shop,
    ) -> QuerySet:
        return (
            ProductSelector
            .base_queryset()
            .filter(
                shop=shop,
                status=Product.Status.ACTIVE,
            )
        )

    @staticmethod
    def get_product_detail(
        *,
        shop,
        product_id,
    ) -> Product:
        return (
            ProductSelector
            .base_queryset()
            .get(
                id=product_id,
                shop=shop,
            )
        )