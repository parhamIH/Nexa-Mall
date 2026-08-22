from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    ProductVariantOptionValue,
)
from apps.tenants.models import Shop, Tenant


class ProductModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
        )
        
        cls.shop = Shop.objects.create(
            name="Test Shop",
            tenant=cls.tenant,
        )

        cls.brand = Brand.objects.create(
            name="Test Brand",
            slug="test-brand",
        )

    def test_product_defaults_to_draft(self):
        product = Product.objects.create(
            shop=self.shop,
            name="Test Product",
            slug="test-product",
            brand=self.brand,
        )

        self.assertEqual(
            product.status,
            Product.Status.DRAFT,
        )

    def test_product_slug_is_unique_per_shop(self):
        Product.objects.create(
            shop=self.shop,
            name="Product One",
            slug="same-slug",
        )

        with self.assertRaises(Exception):
            Product.objects.create(
                shop=self.shop,
                name="Product Two",
                slug="same-slug",
            )

class CategoryModelTests(TestCase):

    def test_category_can_have_parent(self):
        parent = Category.objects.create(
            name="Electronics",
            slug="electronics",
        )

        child = Category.objects.create(
            name="Phones",
            slug="phones",
            parent=parent,
        )

        self.assertEqual(
            child.parent,
            parent,
        )

    def test_category_without_parent_is_root_category(self):
        category = Category.objects.create(
            name="Electronics",
            slug="electronics",
        )

        self.assertIsNone(category.parent)

class ProductOptionModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
        )

        cls.shop = Shop.objects.create(
            name="Test Shop",
            tenant=cls.tenant,
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="T-Shirt",
            slug="t-shirt",
        )

    def test_option_belongs_to_product(self):
        option = ProductOption.objects.create(
            product=self.product,
            name="Color",
            code="color",
        )

        self.assertEqual(
            option.product,
            self.product,
        )

    def test_option_value_belongs_to_option(self):
        option = ProductOption.objects.create(
            product=self.product,
            name="Color",
            code="color",
        )

        value = ProductOptionValue.objects.create(
            option=option,
            value="Black",
            code="black",
        )

        self.assertEqual(
            value.option,
            option,
        )

class ProductVariantModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
        )

        cls.shop = Shop.objects.create(
            name="Test Shop",
            tenant=cls.tenant,
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="T-Shirt",
            slug="t-shirt",
        )

    def test_variant_has_price_and_sku(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            sku="TSHIRT-BLK-M",
            price=Decimal("500000"),
        )

        self.assertEqual(
            variant.sku,
            "TSHIRT-BLK-M",
        )

        self.assertEqual(
            variant.price,
            Decimal("500000"),
        )

    def test_variant_defaults_to_active(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            sku="TSHIRT-BLK-M",
            price=Decimal("500000"),
        )

        self.assertEqual(
            variant.status,
            ProductVariant.Status.ACTIVE,
        )



class ProductVariantOptionValueTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
                    name="Test Tenant",
                )
          
        cls.shop = Shop.objects.create(
            name="Test Shop",
            tenant=cls.tenant,
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="T-Shirt",
            slug="t-shirt",
        )

        cls.option = ProductOption.objects.create(
            product=cls.product,
            name="Color",
            code="color",
        )

        cls.black = ProductOptionValue.objects.create(
            option=cls.option,
            value="Black",
            code="black",
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="TSHIRT-BLACK",
            price=Decimal("500000"),
        )

    def test_variant_can_have_option_value(self):
        link = ProductVariantOptionValue.objects.create(
            variant=self.variant,
            option_value=self.black,
        )

        self.assertEqual(
            link.variant,
            self.variant,
        )

        self.assertEqual(
            link.option_value,
            self.black,
        )