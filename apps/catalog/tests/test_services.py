from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.catalog.models import (
    Product,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
)
from apps.catalog.services.product import ProductService
from apps.catalog.services.variant import VariantService
from apps.tenants.models import Shop, Tenant, TenantMembership


User = get_user_model()


class ProductServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
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
            name="Test Tenant",
        )

        cls.other_tenant = Tenant.objects.create(
            name="Other Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Test Shop",
            slug="test-shop",
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
            name="T-Shirt",
            slug="t-shirt",
        )

    def test_cannot_activate_product_without_active_variant(self):
        with self.assertRaises(ValueError):
            ProductService.activate_product(
                product=self.product
            )

    def test_can_activate_product_with_active_variant(self):
        ProductVariant.objects.create(
            product=self.product,
            sku="TS-001",
            price=Decimal("500000"),
        )

        ProductService.activate_product(
            product=self.product
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.status,
            Product.Status.ACTIVE,
        )

    def test_cannot_reactivate_archived_product(self):
        self.product.status = Product.Status.ARCHIVED
        self.product.save()

        with self.assertRaises(ValueError):
            ProductService.activate_product(
                product=self.product
            )

    # =========================================================
    # Service-level Authorization
    # =========================================================

    def test_employee_cannot_create_product(self):
        with self.assertRaises(PermissionDenied):
            ProductService.create_product(
                shop_id=self.shop.id,
                validated_data={
                    "name": "Forbidden Product",
                    "slug": "forbidden-product",
                    "description": "",
                    "status": Product.Status.DRAFT,
                    "brand": None,
                },
                user=self.employee,
            )

    def test_manager_can_create_product(self):
        product = ProductService.create_product(
            shop_id=self.shop.id,
            validated_data={
                "name": "Manager Product",
                "slug": "manager-product",
                "description": "",
                "status": Product.Status.DRAFT,
                "brand": None,
            },
            user=self.manager,
        )

        self.assertEqual(
            product.shop_id,
            self.shop.id,
        )

    def test_other_tenant_user_cannot_create_product(self):
        with self.assertRaises(PermissionDenied):
            ProductService.create_product(
                shop_id=self.shop.id,
                validated_data={
                    "name": "Cross Tenant Product",
                    "slug": "cross-tenant-product",
                    "description": "",
                    "status": Product.Status.DRAFT,
                    "brand": None,
                },
                user=self.other_user,
            )

    def test_manager_can_update_product(self):
        product = Product.objects.create(
            shop=self.shop,
            name="Old Name",
            slug="old-name",
            status=Product.Status.DRAFT,
        )

        updated = ProductService.update_product(
            product=product,
            validated_data={
                "name": "New Name",
            },
            user=self.manager,
        )

        updated.refresh_from_db()

        self.assertEqual(
            updated.name,
            "New Name",
        )

    def test_other_tenant_user_cannot_update_product(self):
        product = Product.objects.create(
            shop=self.shop,
            name="Protected Product",
            slug="protected-product",
            status=Product.Status.DRAFT,
        )

        with self.assertRaises(PermissionDenied):
            ProductService.update_product(
                product=product,
                validated_data={
                    "name": "Hacked Name",
                },
                user=self.other_user,
            )

        product.refresh_from_db()

        self.assertEqual(
            product.name,
            "Protected Product",
        )

    def test_other_tenant_user_cannot_delete_product(self):
        product = Product.objects.create(
            shop=self.shop,
            name="Protected Product",
            slug="protected-delete",
            status=Product.Status.ARCHIVED,
        )

        with self.assertRaises(PermissionDenied):
            ProductService.delete_product(
                product=product,
                user=self.other_user,
            )

        self.assertTrue(
            Product.objects.filter(
                id=product.id,
            ).exists()
        )

    def test_employee_cannot_update_product_directly(self):
        product = Product.objects.create(
            shop=self.shop,
            name="Employee Protected",
            slug="employee-protected",
            status=Product.Status.DRAFT,
        )

        with self.assertRaises(PermissionDenied):
            ProductService.update_product(
                product=product,
                validated_data={
                    "name": "Unauthorized",
                },
                user=self.employee,
            )

        product.refresh_from_db()

        self.assertEqual(
            product.name,
            "Employee Protected",
        )

    def test_employee_cannot_delete_product_directly(self):
        product = Product.objects.create(
            shop=self.shop,
            name="Employee Delete Protected",
            slug="employee-delete-protected",
            status=Product.Status.ARCHIVED,
        )

        with self.assertRaises(PermissionDenied):
            ProductService.delete_product(
                product=product,
                user=self.employee,
            )

        self.assertTrue(
            Product.objects.filter(
                id=product.id,
            ).exists()
        )


class VariantServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Test Shop",
            slug="test-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="T-Shirt",
            slug="t-shirt",
        )

        cls.color = ProductOption.objects.create(
            product=cls.product,
            name="Color",
            code="color",
        )

        cls.size = ProductOption.objects.create(
            product=cls.product,
            name="Size",
            code="size",
        )

        cls.black = ProductOptionValue.objects.create(
            option=cls.color,
            value="Black",
            code="black",
        )

        cls.white = ProductOptionValue.objects.create(
            option=cls.color,
            value="White",
            code="white",
        )

        cls.size_42 = ProductOptionValue.objects.create(
            option=cls.size,
            value="42",
            code="42",
        )

    def test_variant_can_have_one_value_per_option(self):
        variant = VariantService.create_variant(
            product=self.product,
            sku="TS-BLK-42",
            price=Decimal("500000"),
            option_values=[
                self.black,
                self.size_42,
            ],
        )

        self.assertEqual(
            variant.option_values.count(),
            2,
        )

    def test_variant_cannot_have_two_values_from_same_option(self):
        with self.assertRaises(ValueError):
            VariantService.create_variant(
                product=self.product,
                sku="TS-BLK-WHT",
                price=Decimal("500000"),
                option_values=[
                    self.black,
                    self.white,
                ],
            )

    def test_variant_option_value_must_belong_to_product(self):
        other_product = Product.objects.create(
            shop=self.shop,
            name="Other Product",
            slug="other-product",
        )

        other_option = ProductOption.objects.create(
            product=other_product,
            name="Color",
            code="color",
        )

        other_value = ProductOptionValue.objects.create(
            option=other_option,
            value="Blue",
            code="blue",
        )

        with self.assertRaises(ValueError):
            VariantService.create_variant(
                product=self.product,
                sku="TS-BLUE-42",
                price=Decimal("500000"),
                option_values=[
                    other_value,
                    self.size_42,
                ],
            )