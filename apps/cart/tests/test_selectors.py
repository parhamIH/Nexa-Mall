from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.cart.selectors import CartSelector
from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class CartSelectorTests(TestCase):

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
            price="100000",
        )

    def test_get_active_cart(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=2,
        )

        result = CartSelector.get_active_cart(
            user=self.user,
            shop_id=self.shop.id,
        )

        self.assertEqual(
            result.id,
            cart.id,
        )

        self.assertEqual(
            result.items.count(),
            1,
        )

    def test_get_user_carts(self):
        Cart.objects.create(
            user=self.user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        carts = CartSelector.get_user_carts(
            user=self.user,
        )

        self.assertEqual(
            carts.count(),
            1,
        )