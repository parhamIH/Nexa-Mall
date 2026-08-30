from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class CartModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="customer@example.com",
            password="test-password",
        )

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
            name="Test Product",
            slug="test-product",
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="TEST-001",
            name="Test Variant",
            price="100000",
        )

    def test_create_cart(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        self.assertEqual(
            cart.status,
            Cart.Status.ACTIVE,
        )

        self.assertEqual(
            cart.user,
            self.user,
        )

        self.assertEqual(
            cart.shop,
            self.shop,
        )

    def test_create_cart_item(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        item = CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=2,
        )

        self.assertEqual(item.cart, cart)
        self.assertEqual(item.variant, self.variant)
        self.assertEqual(item.quantity, 2)

    def test_cart_items_relation(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        item = CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=2,
        )

        self.assertIn(
            item,
            cart.items.all(),
        )