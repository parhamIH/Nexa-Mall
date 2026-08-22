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