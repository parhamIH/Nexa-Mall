from django.db.models import QuerySet

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