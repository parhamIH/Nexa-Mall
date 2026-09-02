from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.checkout.services import CheckoutService
from apps.inventory.models import InventoryItem, Reservation
from apps.orders.models import Order, OrderItem
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class CheckoutServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="checkout@example.com",
            password="test-password",
        )

        cls.tenant = Tenant.objects.create(
            name="Checkout Tenant",
        )

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Checkout Shop",
            slug="checkout-shop",
        )

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Checkout Product",
            slug="checkout-product",
            status=Product.Status.ACTIVE,
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="CHECKOUT-001",
            name="Black / XL",
            price=Decimal("500000"),
            status=ProductVariant.Status.ACTIVE,
        )

        cls.inventory = InventoryItem.objects.create(
            variant=cls.variant,
            on_hand=10,
            reserved=0,
        )

    def create_cart(self, quantity=2):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        CartItem.objects.create(
            cart=cart,
            variant=self.variant,
            quantity=quantity,
        )

        return cart

    def test_successful_checkout(self):
        cart = self.create_cart(quantity=2)

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        order.refresh_from_db()
        cart.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.PAYMENT_PENDING,
        )

        self.assertEqual(
            order.subtotal,
            Decimal("1000000"),
        )

        self.assertEqual(
            order.total,
            Decimal("1000000"),
        )

        self.assertEqual(
            order.items.count(),
            1,
        )

        self.assertEqual(
            cart.status,
            Cart.Status.CONVERTED,
        )

        self.assertEqual(
            self.inventory.reserved,
            2,
        )

        self.assertEqual(
            self.inventory.available,
            8,
        )

        self.assertEqual(
            Reservation.objects.filter(
                inventory=self.inventory,
                quantity=2,
                status=Reservation.Status.ACTIVE,
            ).count(),
            1,
        )

    def test_order_item_contains_price_snapshot(self):
        cart = self.create_cart(quantity=2)

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        item = order.items.get()

        self.variant.price = Decimal("700000")
        self.variant.save(
            update_fields=["price"]
        )

        item.refresh_from_db()

        self.assertEqual(
            item.unit_price,
            Decimal("500000"),
        )

        self.assertEqual(
            item.total_price,
            Decimal("1000000"),
        )

    def test_cannot_checkout_empty_cart(self):
        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

    def test_cannot_checkout_converted_cart(self):
        cart = self.create_cart()

        CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

    def test_insufficient_inventory_rolls_back_checkout(self):
        cart = self.create_cart(quantity=11)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

        self.inventory.refresh_from_db()
        cart.refresh_from_db()

        self.assertEqual(
            self.inventory.reserved,
            0,
        )

        self.assertEqual(
            cart.status,
            Cart.Status.ACTIVE,
        )

        self.assertFalse(
            Order.objects.filter(
                user=self.user,
            ).exists()
        )

        self.assertFalse(
            Reservation.objects.filter(
                inventory=self.inventory,
            ).exists()
        )

    def test_cannot_checkout_variant_from_another_shop(self):
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
            sku="OTHER-CHECKOUT-001",
            price=Decimal("100000"),
        )

        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        CartItem.objects.create(
            cart=cart,
            variant=other_variant,
            quantity=1,
        )

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

    def test_checkout_uses_current_variant_price(self):
        cart = self.create_cart(quantity=2)

        self.variant.price = Decimal("600000")
        self.variant.save(
            update_fields=["price"]
        )

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        self.assertEqual(
            order.subtotal,
            Decimal("1200000"),
        )

        item = order.items.get()

        self.assertEqual(
            item.unit_price,
            Decimal("600000"),
        )

    def test_shipping_cost_is_included_in_total(self):
        cart = self.create_cart(quantity=2)

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
            shipping_cost=Decimal("50000"),
        )

        self.assertEqual(
            order.subtotal,
            Decimal("1000000"),
        )

        self.assertEqual(
            order.shipping_cost,
            Decimal("50000"),
        )

        self.assertEqual(
            order.total,
            Decimal("1050000"),
        )
    def test_checkout_creates_one_order_item_per_cart_item(self):
        second_product = Product.objects.create(
            shop=self.shop,
            name="Second Product",
            slug="second-product",
            status=Product.Status.ACTIVE,
        )

        second_variant = ProductVariant.objects.create(
            product=second_product,
            sku="CHECKOUT-002",
            price=Decimal("300000"),
            status=ProductVariant.Status.ACTIVE,
        )

        InventoryItem.objects.create(
            variant=second_variant,
            on_hand=5,
            reserved=0,
        )

        cart = self.create_cart(quantity=2)

        CartItem.objects.create(
            cart=cart,
            variant=second_variant,
            quantity=1,
        )

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        self.assertEqual(
            order.items.count(),
            2,
        )

        self.assertEqual(
            order.subtotal,
            Decimal("1300000"),
        )
    def test_failed_checkout_rolls_back_everything(self):
        cart = self.create_cart(quantity=11)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

        cart.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            cart.status,
            Cart.Status.ACTIVE,
        )

        self.assertEqual(
            self.inventory.reserved,
            0,
        )

        self.assertEqual(
            self.inventory.available,
            10,
        )

        self.assertFalse(
            Order.objects.filter(
                user=self.user,
            ).exists()
        )

        self.assertFalse(
            OrderItem.objects.filter(
                order__user=self.user,
            ).exists()
        )

        self.assertFalse(
            Reservation.objects.filter(
                inventory=self.inventory,
            ).exists()
        )

    def test_cannot_checkout_inactive_product(self):
        self.product.status = Product.Status.DRAFT
        self.product.save(update_fields=["status"])

        cart = self.create_cart(quantity=1)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )


    def test_cannot_checkout_inactive_variant(self):
        self.variant.status = ProductVariant.Status.INACTIVE
        self.variant.save(update_fields=["status"])

        cart = self.create_cart(quantity=1)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )