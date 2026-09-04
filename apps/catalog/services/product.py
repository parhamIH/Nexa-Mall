from django.db import transaction

from apps.catalog.models  import Product, ProductVariant

class ProductService:

    @staticmethod
    @transaction.atomic
    def create_product(
        *,
        shop_id,
        validated_data,
        user,
    ):
        categories = validated_data.pop(
            "categories",
            [],
        )

        product = Product.objects.create(
            shop_id=shop_id,
            **validated_data,
        )

        product.categories.set(categories)

        return product

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


    @staticmethod
    @transaction.atomic
    def update_product(
        *,
        product,
        validated_data,
        user,
    ):
        categories = validated_data.pop(
            "categories",
            None,
        )

        for field, value in validated_data.items():
            setattr(product, field, value)

        product.save()

        if categories is not None:
            product.categories.set(categories)

        return product

    @staticmethod
    @transaction.atomic
    def delete_product(
        *,
        product,
        user,
    ):
        if product.status != Product.Status.ARCHIVED:
            raise ValueError(
                "Only archived products can be deleted."
            )

        product.delete()