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

    def create_cart(
        self,
        *,
        quantity=2,
        user=None,
        shop=None,
        variant=None,
    ):
        cart = Cart.objects.create(
            user=user or self.user,
            shop=shop or self.shop,
        )

        CartItem.objects.create(
            cart=cart,
            variant=variant or self.variant,
            quantity=quantity,
        )

        return cart

    # =========================================================
    # SUCCESS
    # =========================================================

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
            order.discount,
            Decimal("0"),
        )

        self.assertEqual(
            order.shipping_cost,
            Decimal("0"),
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
            self.inventory.on_hand,
            10,
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

    def test_checkout_creates_correct_order_item_snapshot(self):
        cart = self.create_cart(quantity=2)

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        item = order.items.get()

        self.assertEqual(
            item.product_name,
            "Checkout Product",
        )

        self.assertEqual(
            item.variant_name,
            "Black / XL",
        )

        self.assertEqual(
            item.sku,
            "CHECKOUT-001",
        )

        self.assertEqual(
            item.quantity,
            2,
        )

        self.assertEqual(
            item.unit_price,
            Decimal("500000"),
        )

        self.assertEqual(
            item.total_price,
            Decimal("1000000"),
        )

    def test_checkout_preserves_address_snapshot(self):
        cart = self.create_cart(quantity=1)

        shipping_address = {
            "full_name": "Parham",
            "city": "Tehran",
            "address": "Test Street",
            "postal_code": "1234567890",
        }

        billing_address = {
            "full_name": "Parham",
            "city": "Tehran",
            "address": "Billing Street",
        }

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
            shipping_address=shipping_address,
            billing_address=billing_address,
            customer_note="Call before delivery.",
        )

        self.assertEqual(
            order.shipping_address,
            shipping_address,
        )

        self.assertEqual(
            order.billing_address,
            billing_address,
        )

        self.assertEqual(
            order.customer_note,
            "Call before delivery.",
        )

    def test_checkout_with_shipping_cost(self):
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

    # =========================================================
    # PRICE SNAPSHOT
    # =========================================================

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

        item = order.items.get()

        self.assertEqual(
            item.unit_price,
            Decimal("600000"),
        )

        self.assertEqual(
            item.total_price,
            Decimal("1200000"),
        )

        self.assertEqual(
            order.subtotal,
            Decimal("1200000"),
        )

    # =========================================================
    # EMPTY / INVALID CART
    # =========================================================

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

    def test_cannot_checkout_converted_cart_twice(self):
        cart = self.create_cart(quantity=1)

        CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

    def test_cannot_checkout_cart_of_another_user(self):
        cart = self.create_cart(quantity=1)

        other_user = User.objects.create_user(
            email="other@example.com",
            password="test-password",
        )

        with self.assertRaises(Cart.DoesNotExist):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=other_user,
            )

    # =========================================================
    # PRODUCT / VARIANT VALIDATION
    # =========================================================

    def test_cannot_checkout_inactive_product(self):
        self.product.status = Product.Status.DRAFT
        self.product.save(
            update_fields=["status"]
        )

        cart = self.create_cart(quantity=1)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

    def test_cannot_checkout_inactive_variant(self):
        self.variant.status = ProductVariant.Status.INACTIVE
        self.variant.save(
            update_fields=["status"]
        )

        cart = self.create_cart(quantity=1)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
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
            status=Product.Status.ACTIVE,
        )

        other_variant = ProductVariant.objects.create(
            product=other_product,
            sku="OTHER-001",
            price=Decimal("200000"),
            status=ProductVariant.Status.ACTIVE,
        )

        InventoryItem.objects.create(
            variant=other_variant,
            on_hand=5,
            reserved=0,
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

    def test_cannot_checkout_variant_without_inventory(self):
        product = Product.objects.create(
            shop=self.shop,
            name="No Inventory Product",
            slug="no-inventory-product",
            status=Product.Status.ACTIVE,
        )

        variant = ProductVariant.objects.create(
            product=product,
            sku="NO-INVENTORY-001",
            price=Decimal("100000"),
            status=ProductVariant.Status.ACTIVE,
        )

        cart = Cart.objects.create(
            user=self.user,
            shop=self.shop,
        )

        CartItem.objects.create(
            cart=cart,
            variant=variant,
            quantity=1,
        )

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

    # =========================================================
    # INVENTORY
    # =========================================================

    def test_insufficient_inventory_rolls_back_everything(self):
        cart = self.create_cart(quantity=11)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
            )

        self.inventory.refresh_from_db()
        cart.refresh_from_db()

        self.assertEqual(
            self.inventory.on_hand,
            10,
        )

        self.assertEqual(
            self.inventory.reserved,
            0,
        )

        self.assertEqual(
            self.inventory.available,
            10,
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
            OrderItem.objects.filter(
                order__user=self.user,
            ).exists()
        )

        self.assertFalse(
            Reservation.objects.filter(
                inventory=self.inventory,
            ).exists()
        )

    # =========================================================
    # RESERVATION
    # =========================================================

    def test_checkout_creates_reservation(self):
        cart = self.create_cart(quantity=3)

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
            reservation_minutes=20,
        )

        reservation = Reservation.objects.get(
            inventory=self.inventory,
        )

        self.assertEqual(
            reservation.quantity,
            3,
        )

        self.assertEqual(
            reservation.status,
            Reservation.Status.ACTIVE,
        )

        self.assertTrue(
            reservation.reference.startswith(
                f"{order.order_number}:"
            )
        )

    def test_invalid_reservation_duration_rolls_back(self):
        cart = self.create_cart(quantity=2)

        with self.assertRaises(ValidationError):
            CheckoutService.start_checkout(
                cart_id=cart.id,
                user=self.user,
                reservation_minutes=0,
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

    # =========================================================
    # MULTI ITEM
    # =========================================================

    def test_checkout_multiple_items(self):
        second_product = Product.objects.create(
            shop=self.shop,
            name="Second Product",
            slug="second-product",
            status=Product.Status.ACTIVE,
        )

        second_variant = ProductVariant.objects.create(
            product=second_product,
            sku="CHECKOUT-002",
            name="Second Variant",
            price=Decimal("300000"),
            status=ProductVariant.Status.ACTIVE,
        )

        second_inventory = InventoryItem.objects.create(
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

        self.inventory.refresh_from_db()
        second_inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.reserved,
            2,
        )

        self.assertEqual(
            second_inventory.reserved,
            1,
        )

    # =========================================================
    # CUSTOMER / SHOP
    # =========================================================

    def test_checkout_order_belongs_to_cart_shop(self):
        cart = self.create_cart(quantity=1)

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        self.assertEqual(
            order.shop_id,
            self.shop.id,
        )

    def test_checkout_order_belongs_to_customer(self):
        cart = self.create_cart(quantity=1)

        order = CheckoutService.start_checkout(
            cart_id=cart.id,
            user=self.user,
        )

        self.assertEqual(
            order.user_id,
            self.user.id,
        )