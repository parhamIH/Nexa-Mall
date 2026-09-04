from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.cart.services import CartItemService
from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class CartAPIPermissionTests(TestCase):
    """
    Cross-shop isolation for the cart API.

    POST /api/v1/cart/shops/A/items/ with a variant that belongs
    to shop B must be rejected.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="customer@example.com",
            password="test-password",
        )

        cls.other_user = User.objects.create_user(
            email="intruder@example.com",
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

        cls.other_shop = Shop.objects.create(
            tenant=cls.other_tenant,
            name="Other Shop",
            slug="other-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Test Product",
            slug="test-product",
        )

        cls.other_product = Product.objects.create(
            shop=cls.other_shop,
            name="Other Product",
            slug="other-product",
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="TEST-001",
            price="100000",
        )

        cls.other_variant = ProductVariant.objects.create(
            product=cls.other_product,
            sku="OTHER-001",
            price="200000",
        )

    def setUp(self):
        self.client = APIClient()

    def items_url(self):
        return (
            f"/api/v1/cart/shops/"
            f"{self.shop.id}/items/"
        )

    def test_cannot_add_variant_from_other_shop(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            self.items_url(),
            {
                "variant_id": str(self.other_variant.id),
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            CartItem.objects.filter(
                variant=self.other_variant,
            ).exists()
        )

    def test_cannot_add_variant_to_unknown_shop(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            f"/api/v1/cart/shops/"
            f"00000000-0000-0000-0000-000000000000/items/",
            {
                "variant_id": str(self.variant.id),
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_service_rejects_item_owned_by_other_user(self):
        cart = Cart.objects.create(
            user=self.other_user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        item = CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=1,
        )

        with self.assertRaises(PermissionDenied):
            CartItemService.set_quantity(
                item=item,
                quantity=5,
                user=self.user,
            )

        with self.assertRaises(PermissionDenied):
            CartItemService.remove_item(
                item=item,
                user=self.user,
            )

        self.assertTrue(
            CartItem.objects.filter(
                id=item.id,
            ).exists()
        )

    def test_owner_can_modify_own_item(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        item = CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=1,
        )

        updated = CartItemService.set_quantity(
            item=item,
            quantity=5,
            user=self.user,
        )

        self.assertEqual(
            updated.quantity,
            5,
        )

        CartItemService.remove_item(
            item=updated,
            user=self.user,
        )

        self.assertFalse(
            CartItem.objects.filter(
                id=item.id,
            ).exists()
        )