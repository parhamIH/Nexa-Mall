from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.tenants.models import TenantMembership
from apps.tenants.services.access import TenantAccessService


class IsActiveShopMember(BasePermission):
    """
    User must be an active member of the object's shop tenant.
    """

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
    """
    Active OWNER or MANAGER can modify shop-owned resources.
    All active members can read them.
    """

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