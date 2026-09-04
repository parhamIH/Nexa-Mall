from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class CartAPITests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="customer@example.com",
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
            name="Test Variant",
            price="100000",
        )

        cls.other_variant = ProductVariant.objects.create(
            product=cls.other_product,
            sku="OTHER-001",
            name="Other Variant",
            price="200000",
        )

    def setUp(self):
        self.client = APIClient()

    def cart_url(self):
        return (
            f"/api/v1/cart/shops/"
            f"{self.shop.id}/"
        )

    def items_url(self):
        return (
            f"/api/v1/cart/shops/"
            f"{self.shop.id}/items/"
        )

    def item_url(self, item):
        return (
            f"/api/v1/cart/items/"
            f"{item.id}/"
        )

    def test_get_cart(self):
        self.client.force_authenticate(
            user=self.user,
        )

        self.client.post(
            self.items_url(),
            {
                "variant_id": str(self.variant.id),
                "quantity": 2,
            },
            format="json",
        )

        response = self.client.get(
            self.cart_url(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["status"],
            Cart.Status.ACTIVE,
        )

        self.assertEqual(
            len(response.data["items"]),
            1,
        )

    def test_get_cart_returns_404_when_no_active_cart(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.get(
            self.cart_url(),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_add_item(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            self.items_url(),
            {
                "variant_id": str(self.variant.id),
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["quantity"],
            2,
        )

        self.assertEqual(
            response.data["sku"],
            "TEST-001",
        )

        self.assertEqual(
            response.data["product_name"],
            "Test Product",
        )

    def test_add_same_item_increments_quantity(self):
        self.client.force_authenticate(
            user=self.user,
        )

        self.client.post(
            self.items_url(),
            {
                "variant_id": str(self.variant.id),
                "quantity": 2,
            },
            format="json",
        )

        response = self.client.post(
            self.items_url(),
            {
                "variant_id": str(self.variant.id),
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["quantity"],
            5,
        )

        cart = Cart.objects.get(
            user=self.user,
            shop=self.shop,
        )

        self.assertEqual(
            cart.items.count(),
            1,
        )

    def test_update_quantity(self):
        self.client.force_authenticate(
            user=self.user,
        )

        self.client.post(
            self.items_url(),
            {
                "variant_id": str(self.variant.id),
                "quantity": 2,
            },
            format="json",
        )

        item = CartItem.objects.get(
            cart__user=self.user,
            variant=self.variant,
        )

        response = self.client.patch(
            self.item_url(item),
            {
                "quantity": 7,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["quantity"],
            7,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            7,
        )

    def test_delete_item(self):
        self.client.force_authenticate(
            user=self.user,
        )

        self.client.post(
            self.items_url(),
            {
                "variant_id": str(self.variant.id),
                "quantity": 2,
            },
            format="json",
        )

        item = CartItem.objects.get(
            cart__user=self.user,
            variant=self.variant,
        )

        response = self.client.delete(
            self.item_url(item),
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            CartItem.objects.filter(
                id=item.id,
            ).exists()
        )

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(
            self.cart_url(),
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_user_cannot_access_other_users_item(self):
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

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.patch(
            self.item_url(item),
            {
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        response = self.client.delete(
            self.item_url(item),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            CartItem.objects.filter(
                id=item.id,
            ).exists()
        )

    def test_user_cannot_get_other_users_cart(self):
        Cart.objects.create(
            user=self.other_user,
            shop=self.shop,
            status=Cart.Status.ACTIVE,
        )

        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.get(
            self.cart_url(),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_add_item_with_unknown_variant_returns_404(self):
        self.client.force_authenticate(
            user=self.user,
        )

        response = self.client.post(
            self.items_url(),
            {
                "variant_id": "00000000-0000-0000-0000-000000000000",
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )
