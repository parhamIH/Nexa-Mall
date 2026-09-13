from django.db import transaction

from apps.catalog.cache import invalidate_product
from apps.catalog.models  import (
    ProductOptionValue,
    ProductVariant,
)

class VariantService:

    @staticmethod
    @transaction.atomic
    def create_variant(
        *,
        product,
        sku,
        price,
        option_values=None,
        name="",
        compare_at_price=None,
        weight_grams=0,
    ):
        option_values = list(option_values or [])

        VariantService._validate_option_values(
            product=product,
            option_values=option_values,
        )

        variant = ProductVariant.objects.create(
            product=product,
            sku=sku,
            name=name,
            price=price,
            compare_at_price=compare_at_price,
            weight_grams=weight_grams,
        )

        if option_values:
            variant.option_values.set(option_values)

        # A new variant changes the product detail representation
        # (variant list, count, min price); invalidate on commit.
        invalidate_product(
            product_id=product.id,
        )

        return variant

    @staticmethod
    @transaction.atomic
    def update_variant(
        *,
        variant,
        validated_data,
    ):
        variant = (
            ProductVariant.objects
            .select_for_update()
            .get(id=variant.id)
        )

        for field, value in validated_data.items():
            setattr(variant, field, value)

        variant.save()

        # The variant did not change, but the product representation
        # derived from it did (prices live in the detail payload).
        invalidate_product(
            product_id=variant.product_id,
        )

        return variant

    @staticmethod
    @transaction.atomic
    def delete_variant(
        *,
        variant,
    ):
        variant = (
            ProductVariant.objects
            .select_for_update()
            .get(id=variant.id)
        )

        # Capture the parent id before delete: after Model.delete()
        # the row is gone, and the relation must not be re-queried
        # for the invalidation target.
        product_id = variant.product_id

        variant.delete()

        invalidate_product(
            product_id=product_id,
        )

    @staticmethod
    def _validate_option_values(
        *,
        product,
        option_values,
    ):
        option_value_ids = {
            option_value.id
            for option_value in option_values
        }

        if len(option_value_ids) != len(option_values):
            raise ValueError(
                "Duplicate option values are not allowed."
            )

        valid_count = ProductOptionValue.objects.filter(
            id__in=option_value_ids,
            option__product=product,
        ).count()

        if valid_count != len(option_values):
            raise ValueError(
                "All option values must belong to the product."
            )

        option_ids = [
            option_value.option_id
            for option_value in option_values
        ]

        if len(option_ids) != len(set(option_ids)):
            raise ValueError(
                "A variant cannot contain multiple values "
                "from the same option."
            )