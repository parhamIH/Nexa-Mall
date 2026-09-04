from django.core.exceptions import PermissionDenied

from apps.tenants.models import TenantMembership


class TenantAccessService:

    @staticmethod
    def get_membership(
        *,
        user,
        tenant,
    ):
        if not user.is_authenticated:
            return None

        if user.is_superuser:
            return None

        return (
            TenantMembership.objects
            .filter(
                user=user,
                tenant=tenant,
                is_active=True,
            )
            .first()
        )

    @staticmethod
    def has_membership(
        *,
        user,
        tenant,
    ):
        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return TenantMembership.objects.filter(
            user=user,
            tenant=tenant,
            is_active=True,
        ).exists()

    @staticmethod
    def has_role(
        *,
        user,
        tenant,
        roles,
    ):
        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return TenantMembership.objects.filter(
            user=user,
            tenant=tenant,
            role__in=roles,
            is_active=True,
        ).exists()

    @staticmethod
    def require_membership(
        *,
        user,
        tenant,
    ):
        if not TenantAccessService.has_membership(
            user=user,
            tenant=tenant,
        ):
            raise PermissionDenied(
                "You do not have access to this tenant."
            )