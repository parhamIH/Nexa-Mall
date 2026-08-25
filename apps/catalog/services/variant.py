from django.db import transaction

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

        return variant

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