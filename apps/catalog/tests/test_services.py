from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import (
    Product,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
)
from apps.catalog.services.product import ProductService
from apps.catalog.services.variant import VariantService
from apps.tenants.models import Shop, Tenant


class ProductServiceTests(TestCase):

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