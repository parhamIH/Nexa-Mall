from django.db import transaction

from apps.catalog.models  import Product, ProductVariant


class ProductService:

    @staticmethod
    @transaction.atomic
    def create_product(
        *,
        shop,
        name,
        slug,
        description="",
        brand=None,
    ):
        return Product.objects.create(
            shop=shop,
            name=name,
            slug=slug,
            description=description,
            brand=brand,
            status=Product.Status.DRAFT,
        )

    @staticmethod
    @transaction.atomic
    def activate_product(*, product):
        if product.status == Product.Status.ARCHIVED:
            raise ValueError(
                "Archived products cannot be activated."
            )

        has_active_variant = product.variants.filter(
            status=ProductVariant.Status.ACTIVE
        ).exists()

        if not has_active_variant:
            raise ValueError(
                "Product must have at least one active variant."
            )

        product.status = Product.Status.ACTIVE

        product.save(
            update_fields=["status", "updated_at"]
        )

        return product

    @staticmethod
    @transaction.atomic
    def archive_product(*, product):
        product.status = Product.Status.ARCHIVED

        product.save(
            update_fields=["status", "updated_at"]
        )

        return product