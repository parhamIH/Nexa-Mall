from django.db.models import (
    Count,
    Min,
    QuerySet,
)

from apps.catalog.models  import Product


class ProductSelector:

    @staticmethod
    def get_by_id(
        *,
        product_id,
    ) -> Product:
        return (
            Product.objects
            .with_relations()
            .get(id=product_id)
        )

    @staticmethod
    def public_product_detail(
        *,
        product_id,
    ):
        """
        Detail read model for the public API.

        The aggregate values the detail serializer exposes
        (variant_count, min_variant_price) are computed by the
        DATABASE in the same query (COUNT/MIN over a single join),
        not by iterating related rows in Python. Query budget is
        fixed regardless of variant count: 1 main query
        (product + shop + brand + annotations) plus one prefetch
        query per relation (categories, images, variants).

        The prefetches stay: the serializer also embeds the variant
        rows themselves, so the joined aggregates and the prefetched
        lists serve different fields.
        """
        return (
            Product.objects
            .filter(
                id=product_id,
                status=Product.Status.ACTIVE,
            )
            .select_related(
                "shop",
                "brand",
            )
            .prefetch_related(
                "categories",
                "images",
                "variants",
            )
            .annotate(
                variant_count=Count(
                    "variants",
                ),
                min_variant_price=Min(
                    "variants__price",
                ),
            )
            .first()
        )

    @staticmethod
    def get_shop_products(
        *,
        shop,
    ) -> QuerySet:
        return (
            Product.objects
            .for_shop(shop)
            .with_relations()
        )

    @staticmethod
    def get_active_products(
        *,
        shop,
    ) -> QuerySet:
        return (
            Product.objects
            .for_shop(shop)
            .active()
            .with_relations()
        )

    @staticmethod
    def get_product_detail(
        *,
        shop,
        product_id,
    ) -> Product:
        return (
            Product.objects
            .for_shop(shop)
            .with_relations()
            .get(id=product_id)
        )
    
    @staticmethod
    def public_products() -> QuerySet:
        return (
            Product.objects
            .filter(
                status=Product.Status.ACTIVE,
            )
            .select_related(
                "shop",
                "brand",
            )
            .prefetch_related(
                "categories",
                "images",
                # Consumed by ProductDetailSerializer's method
                # fields: prefetch keeps the representation build
                # query-free (no N+1 per SerializerMethodField).
                "variants",
            )
            .order_by(
                "-created_at",
                "id",
            )
        )

    @staticmethod
    def products_for_user(
        *,
        user,
    ) -> QuerySet:
        return (
            Product.objects
            .filter(
                shop__tenant__memberships__user=user,
                shop__tenant__memberships__is_active=True,
            )
            .select_related(
                "shop",
                "brand",
            )
            .prefetch_related(
                "categories",
                "images",
            )
            .order_by(
                "-created_at",
                "id",
            )
            .distinct()
        )

    @staticmethod
    def management_products(
        *,
        user,
        shop_id,
    ):
        return (
            Product.objects
            .filter(
                shop_id=shop_id,
                shop__tenant__memberships__user=user,
                shop__tenant__memberships__is_active=True,
            )
            .select_related(
                "shop",
                "brand",
            )
            .prefetch_related(
                "categories",
                "images",
            )
            .order_by(
                "-created_at",
                "id",
            )
            .distinct()
        )