from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import Shop, TenantMembership
from apps.tenants.services.access import TenantAccessService


class ProductService:

    WRITE_ROLES = {
        TenantMembership.Role.OWNER,
        TenantMembership.Role.MANAGER,
    }

    @staticmethod
    def _require_shop_write_access(
        *,
        user,
        shop,
    ):
        allowed = TenantAccessService.has_role(
            user=user,
            tenant=shop.tenant,
            roles=ProductService.WRITE_ROLES,
        )

        if not allowed:
            raise PermissionDenied(
                "You do not have permission to manage "
                "products for this shop."
            )

    @staticmethod
    @transaction.atomic
    def create_product(
        *,
        shop_id,
        validated_data,
        user,
    ):
        shop = (
            Shop.objects
            .select_related("tenant")
            .get(id=shop_id)
        )

        ProductService._require_shop_write_access(
            user=user,
            shop=shop,
        )

        categories = validated_data.pop(
            "categories",
            [],
        )

        product = Product.objects.create(
            shop=shop,
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
        product = (
            Product.objects
            .select_for_update()
            .select_related("shop", "shop__tenant")
            .get(id=product.id)
        )

        ProductService._require_shop_write_access(
            user=user,
            shop=product.shop,
        )

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
        product = (
            Product.objects
            .select_for_update()
            .select_related("shop", "shop__tenant")
            .get(id=product.id)
        )

        ProductService._require_shop_write_access(
            user=user,
            shop=product.shop,
        )

        if product.status != Product.Status.ARCHIVED:
            raise ValueError(
                "Only archived products can be deleted."
            )

        product.delete()