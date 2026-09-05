from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.tenants.models import TenantMembership
from apps.tenants.services.access import TenantAccessService


class IsActiveShopMember(BasePermission):

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        shop = getattr(obj, "shop", None)

        if shop is None:
            return False

        return TenantAccessService.has_membership(
            user=request.user,
            tenant=shop.tenant,
        )


class IsShopManager(BasePermission):

    WRITE_ROLES = {
        TenantMembership.Role.OWNER,
        TenantMembership.Role.MANAGER,
    }

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        shop = getattr(obj, "shop", None)

        if shop is None:
            return False

        if request.method in SAFE_METHODS:
            return TenantAccessService.has_membership(
                user=request.user,
                tenant=shop.tenant,
            )

        return TenantAccessService.has_role(
            user=request.user,
            tenant=shop.tenant,
            roles=self.WRITE_ROLES,
        )




class CanManageShopCatalog(BasePermission):
    """
    Only active OWNER or MANAGER of the shop's tenant
    can manage catalog resources.
    """

    allowed_roles = {
        TenantMembership.Role.OWNER,
        TenantMembership.Role.MANAGER,
    }

    def has_permission(self, request, view):
        shop_id = view.kwargs.get("shop_id")

        if not shop_id:
            return False

        try:
            from apps.tenants.models import Shop

            shop = Shop.objects.select_related("tenant").get(
                id=shop_id,
            )
        except Shop.DoesNotExist:
            return False

        return TenantAccessService.has_role(
            user=request.user,
            tenant=shop.tenant,
            roles=self.allowed_roles,
        )


class CanManageShopOrders(BasePermission):
    """
    Only active OWNER or MANAGER of the shop's tenant
    can view shop orders.
    """

    allowed_roles = {
        TenantMembership.Role.OWNER,
        TenantMembership.Role.MANAGER,
    }

    def has_permission(self, request, view):
        shop_id = view.kwargs.get("shop_id")

        if not shop_id:
            return False

        from apps.tenants.models import Shop

        shop = (
            Shop.objects
            .select_related("tenant")
            .filter(id=shop_id)
            .first()
        )

        if shop is None:
            return False

        return TenantAccessService.has_role(
            user=request.user,
            tenant=shop.tenant,
            roles=self.allowed_roles,
        )