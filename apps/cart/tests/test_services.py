from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cart.models import Cart
from apps.cart.services import CartItemService, CartService
from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class CartServiceTests(TestCase):

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

    def test_get_or_create_cart_returns_same_active_cart(self):
        cart1 = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        cart2 = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        self.assertEqual(
            cart1.id,
            cart2.id,
        )

    def test_add_item(self):
        cart = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        item = CartItemService.add_item(
            cart=cart,
            variant=self.variant,
            quantity=2,
        )

        self.assertEqual(
            item.quantity,
            2,
        )

    def test_add_same_variant_increments_quantity(self):
        cart = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        CartItemService.add_item(
            cart=cart,
            variant=self.variant,
            quantity=2,
        )

        item = CartItemService.add_item(
            cart=cart,
            variant=self.variant,
            quantity=3,
        )

        self.assertEqual(
            item.quantity,
            5,
        )

        self.assertEqual(
            cart.items.count(),
            1,
        )

    def test_cannot_add_variant_from_another_shop(self):
        other_tenant = Tenant.objects.create(
            name="Other Tenant",
        )

        other_shop = Shop.objects.create(
            tenant=other_tenant,
            name="Other Shop",
            slug="other-shop",
        )

        other_product = Product.objects.create(
            shop=other_shop,
            name="Other Product",
            slug="other-product",
        )

        other_variant = ProductVariant.objects.create(
            product=other_product,
            sku="OTHER-001",
            price="200000",
        )

        cart = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        with self.assertRaises(ValidationError):
            CartItemService.add_item(
                cart=cart,
                variant=other_variant,
                quantity=1,
            )

    def test_cannot_add_to_inactive_cart(self):
        cart = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        CartService.abandon_cart(cart=cart)

        with self.assertRaises(ValidationError):
            CartItemService.add_item(
                cart=cart,
                variant=self.variant,
                quantity=1,
            )

    def test_abandon_cart(self):
        cart = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        CartService.abandon_cart(cart=cart)

        cart.refresh_from_db()

        self.assertEqual(
            cart.status,
            Cart.Status.ABANDONED,
        )

    def test_cannot_abandon_non_active_cart(self):
        cart = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        CartService.abandon_cart(cart=cart)

        with self.assertRaises(ValueError):
            CartService.abandon_cart(cart=cart)

    def test_convert_cart(self):
        cart = CartService.get_or_create_cart(
            user=self.user,
            shop=self.shop,
        )

        CartService.mark_converted(cart=cart)

        cart.refresh_from_db()

        self.assertEqual(
            cart.status,
            Cart.Status.CONVERTED,
        )