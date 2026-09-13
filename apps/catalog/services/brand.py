from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.catalog.cache import (
    invalidate_brand_products,
    invalidate_products,
)
from apps.catalog.models import Brand


class BrandService:

    @staticmethod
    @transaction.atomic
    def create_brand(
        *,
        validated_data,
    ):
        # No product can reference the brand before it exists, so
        # there is nothing to invalidate on create.
        return Brand.objects.create(
            **validated_data,
        )

    @staticmethod
    @transaction.atomic
    def update_brand(
        *,
        brand,
        validated_data,
    ):
        brand = (
            Brand.objects
            .select_for_update()
            .get(id=brand.id)
        )

        # Collect the affected products BEFORE the mutation and
        # register the fan-out invalidation: brand_name is part of
        # every referencing product's detail representation.
        invalidate_brand_products(
            brand_id=brand.id,
        )

        for field, value in validated_data.items():
            setattr(brand, field, value)

        brand.save()

        return brand

    @staticmethod
    @transaction.atomic
    def delete_brand(
        *,
        brand,
    ):
        brand = (
            Brand.objects
            .select_for_update()
            .get(id=brand.id)
        )

        # Product.brand is PROTECT: as long as products reference
        # the brand, deletion must fail loudly instead of silently
        # breaking their representation source.
        if brand.products.exists():
            raise ValueError(
                "Only brands without products can be deleted."
            )

        # No referencing products remain; collect (empty) set before
        # delete for consistency with the invalidation pattern.
        product_ids = tuple(
            brand.products.values_list(
                "id",
                flat=True,
            )
        )

        brand.delete()

        invalidate_products(
            product_ids=product_ids,
        )