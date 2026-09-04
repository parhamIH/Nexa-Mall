from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.catalog.models import Product
from apps.tenants.api.permissions import (
    IsActiveShopMember,
    IsShopManager,
)
from apps.tenants.models import Shop, Tenant, TenantMembership
from apps.tenants.services.access import TenantAccessService


User = get_user_model()


class TenantAccessServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="owner@example.com",
            password="test-password",
        )

        cls.manager = User.objects.create_user(
            email="manager@example.com",
            password="test-password",
        )

        cls.employee = User.objects.create_user(
            email="employee@example.com",
            password="test-password",
        )

        cls.other_user = User.objects.create_user(
            email="other@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Tenant A",
        )

        cls.other_tenant = Tenant.objects.create(
            name="Tenant B",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Shop A",
            slug="shop-a",
        )

        cls.other_shop = Shop.objects.create(
            tenant=cls.other_tenant,
            name="Shop B",
            slug="shop-b",
        )

        TenantMembership.objects.create(
            user=cls.owner,
            tenant=cls.tenant,
            role=TenantMembership.Role.OWNER,
        )

        TenantMembership.objects.create(
            user=cls.manager,
            tenant=cls.tenant,
            role=TenantMembership.Role.MANAGER,
        )

        TenantMembership.objects.create(
            user=cls.employee,
            tenant=cls.tenant,
            role=TenantMembership.Role.EMPLOYEE,
        )

        TenantMembership.objects.create(
            user=cls.other_user,
            tenant=cls.other_tenant,
            role=TenantMembership.Role.OWNER,
        )

    def test_owner_has_membership(self):
        self.assertTrue(
            TenantAccessService.has_membership(
                user=self.owner,
                tenant=self.tenant,
            )
        )

    def test_manager_has_membership(self):
        self.assertTrue(
            TenantAccessService.has_membership(
                user=self.manager,
                tenant=self.tenant,
            )
        )

    def test_employee_has_membership(self):
        self.assertTrue(
            TenantAccessService.has_membership(
                user=self.employee,
                tenant=self.tenant,
            )
        )

    def test_user_from_other_tenant_has_no_membership(self):
        self.assertFalse(
            TenantAccessService.has_membership(
                user=self.other_user,
                tenant=self.tenant,
            )
        )

    def test_manager_has_manager_role(self):
        self.assertTrue(
            TenantAccessService.has_role(
                user=self.manager,
                tenant=self.tenant,
                roles={
                    TenantMembership.Role.MANAGER,
                },
            )
        )

    def test_employee_does_not_have_manager_role(self):
        self.assertFalse(
            TenantAccessService.has_role(
                user=self.employee,
                tenant=self.tenant,
                roles={
                    TenantMembership.Role.MANAGER,
                    TenantMembership.Role.OWNER,
                },
            )
        )

    def test_owner_has_write_role(self):
        self.assertTrue(
            TenantAccessService.has_role(
                user=self.owner,
                tenant=self.tenant,
                roles={
                    TenantMembership.Role.MANAGER,
                    TenantMembership.Role.OWNER,
                },
            )
        )


class ShopPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="permission-owner@example.com",
            password="test-password",
        )

        cls.manager = User.objects.create_user(
            email="permission-manager@example.com",
            password="test-password",
        )

        cls.employee = User.objects.create_user(
            email="permission-employee@example.com",
            password="test-password",
        )

        cls.other_user = User.objects.create_user(
            email="permission-other@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Permission Tenant",
        )

        cls.other_tenant = Tenant.objects.create(
            name="Other Permission Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Permission Shop",
            slug="permission-shop",
        )

        cls.other_shop = Shop.objects.create(
            tenant=cls.other_tenant,
            name="Other Permission Shop",
            slug="other-permission-shop",
        )

        TenantMembership.objects.create(
            user=cls.owner,
            tenant=cls.tenant,
            role=TenantMembership.Role.OWNER,
        )

        TenantMembership.objects.create(
            user=cls.manager,
            tenant=cls.tenant,
            role=TenantMembership.Role.MANAGER,
        )

        TenantMembership.objects.create(
            user=cls.employee,
            tenant=cls.tenant,
            role=TenantMembership.Role.EMPLOYEE,
        )

        TenantMembership.objects.create(
            user=cls.other_user,
            tenant=cls.other_tenant,
            role=TenantMembership.Role.OWNER,
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Permission Product",
            slug="permission-product",
        )

        cls.other_product = Product.objects.create(
            shop=cls.other_shop,
            name="Other Product",
            slug="other-product",
        )

    def build_request(self, user, method="GET"):
        factory = APIRequestFactory()

        request = getattr(
            factory,
            method.lower(),
        )("/test/")

        request.user = user

        return request

    def test_active_member_can_read_object(self):
        permission = IsActiveShopMember()

        request = self.build_request(
            self.employee,
            "GET",
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                None,
                self.product,
            )
        )

    def test_employee_can_not_write(self):
        permission = IsShopManager()

        request = self.build_request(
            self.employee,
            "PATCH",
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                None,
                self.product,
            )
        )

    def test_manager_can_write(self):
        permission = IsShopManager()

        request = self.build_request(
            self.manager,
            "PATCH",
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                None,
                self.product,
            )
        )

    def test_owner_can_write(self):
        permission = IsShopManager()

        request = self.build_request(
            self.owner,
            "DELETE",
        )

        self.assertTrue(
            permission.has_object_permission(
                request,
                None,
                self.product,
            )
        )

    def test_user_from_other_tenant_cannot_access_object(self):
        permission = IsActiveShopMember()

        request = self.build_request(
            self.other_user,
            "GET",
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                None,
                self.product,
            )
        )

    def test_user_from_other_tenant_cannot_write_object(self):
        permission = IsShopManager()

        request = self.build_request(
            self.other_user,
            "PATCH",
        )

        self.assertFalse(
            permission.has_object_permission(
                request,
                None,
                self.product,
            )
        )


class ProductScopeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="scope@example.com",
            password="test-password",
        )

        cls.tenant_a = Tenant.objects.create(
            name="Scope Tenant A",
        )

        cls.tenant_b = Tenant.objects.create(
            name="Scope Tenant B",
        )

        cls.shop_a = Shop.objects.create(
            tenant=cls.tenant_a,
            name="Scope Shop A",
            slug="scope-shop-a",
        )

        cls.shop_b = Shop.objects.create(
            tenant=cls.tenant_b,
            name="Scope Shop B",
            slug="scope-shop-b",
        )

        TenantMembership.objects.create(
            user=cls.user,
            tenant=cls.tenant_a,
            role=TenantMembership.Role.MANAGER,
        )

        cls.product_a = Product.objects.create(
            shop=cls.shop_a,
            name="Visible Product",
            slug="visible-product",
        )

        cls.product_b = Product.objects.create(
            shop=cls.shop_b,
            name="Hidden Product",
            slug="hidden-product",
        )

    def test_user_queryset_is_scoped_to_authorized_tenants(self):
        from apps.catalog.selectors.product import ProductSelector

        queryset = ProductSelector.products_for_user(
            user=self.user,
        )

        product_ids = set(
            queryset.values_list(
                "id",
                flat=True,
            )
        )

        self.assertIn(
            self.product_a.id,
            product_ids,
        )

        self.assertNotIn(
            self.product_b.id,
            product_ids,
        )