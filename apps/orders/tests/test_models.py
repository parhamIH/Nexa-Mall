from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from apps.orders.models import Order, OrderItem
from apps.tenants.models import Shop, Tenant


User = get_user_model()


class OrderModelTests(TestCase):

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
            name="Test T-Shirt",
            slug="test-t-shirt",
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="TSHIRT-BLK-XL",
            name="Black / XL",
            price=Decimal("500000.00"),
        )

    def test_create_order(self):
        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
            subtotal=Decimal("1000000.00"),
            discount=Decimal("100000.00"),
            shipping_cost=Decimal("50000.00"),
            total=Decimal("950000.00"),
        )

        self.assertIsNotNone(order.id)

        self.assertEqual(
            order.status,
            Order.Status.PENDING,
        )

        self.assertEqual(
            order.shop,
            self.shop,
        )

        self.assertEqual(
            order.user,
            self.user,
        )

        self.assertEqual(
            order.subtotal,
            Decimal("1000000.00"),
        )

        self.assertEqual(
            order.discount,
            Decimal("100000.00"),
        )

        self.assertEqual(
            order.shipping_cost,
            Decimal("50000.00"),
        )

        self.assertEqual(
            order.total,
            Decimal("950000.00"),
        )

    def test_order_status_choices(self):
        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
        )

        self.assertEqual(
            order.status,
            Order.Status.PENDING,
        )

        order.status = Order.Status.PAYMENT_PENDING
        order.save(update_fields=["status"])

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.PAYMENT_PENDING,
        )

    def test_order_belongs_to_shop(self):
        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
        )

        self.assertEqual(
            order.shop,
            self.shop,
        )

        self.assertIn(
            order,
            self.shop.orders.all(),
        )

    def test_order_belongs_to_user(self):
        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
        )

        self.assertIn(
            order,
            self.user.orders.all(),
        )


class OrderItemModelTests(TestCase):

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
            name="Test T-Shirt",
            slug="test-t-shirt",
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="TSHIRT-BLK-XL",
            name="Black / XL",
            price=Decimal("500000.00"),
        )

        cls.order = Order.objects.create(
            shop=cls.shop,
            user=cls.user,
            subtotal=Decimal("1000000.00"),
            total=Decimal("1000000.00"),
        )

    def test_create_order_item(self):
        item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Test T-Shirt",
            variant_name="Black / XL",
            sku="TSHIRT-BLK-XL",
            quantity=2,
            unit_price=Decimal("500000.00"),
            total_price=Decimal("1000000.00"),
        )

        self.assertIsNotNone(item.id)

        self.assertEqual(
            item.order,
            self.order,
        )

        self.assertEqual(
            item.variant,
            self.variant,
        )

        self.assertEqual(
            item.product_name,
            "Test T-Shirt",
        )

        self.assertEqual(
            item.variant_name,
            "Black / XL",
        )

        self.assertEqual(
            item.sku,
            "TSHIRT-BLK-XL",
        )

        self.assertEqual(
            item.quantity,
            2,
        )

        self.assertEqual(
            item.unit_price,
            Decimal("500000.00"),
        )

        self.assertEqual(
            item.total_price,
            Decimal("1000000.00"),
        )

    def test_order_items_relation(self):
        item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Test T-Shirt",
            variant_name="Black / XL",
            sku="TSHIRT-BLK-XL",
            quantity=2,
            unit_price=Decimal("500000.00"),
            total_price=Decimal("1000000.00"),
        )

        self.assertIn(
            item,
            self.order.items.all(),
        )

    def test_order_item_preserves_product_snapshot(self):
        item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Test T-Shirt",
            variant_name="Black / XL",
            sku="TSHIRT-BLK-XL",
            quantity=2,
            unit_price=Decimal("500000.00"),
            total_price=Decimal("1000000.00"),
        )

        # تغییر محصول اصلی
        self.product.name = "New Product Name"
        self.product.save(update_fields=["name"])

        # Snapshot سفارش نباید تغییر کند
        item.refresh_from_db()

        self.assertEqual(
            item.product_name,
            "Test T-Shirt",
        )

        self.assertEqual(
            item.variant_name,
            "Black / XL",
        )

        self.assertEqual(
            item.sku,
            "TSHIRT-BLK-XL",
        )

    def test_order_item_price_is_snapshot(self):
        item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Test T-Shirt",
            variant_name="Black / XL",
            sku="TSHIRT-BLK-XL",
            quantity=2,
            unit_price=Decimal("500000.00"),
            total_price=Decimal("1000000.00"),
        )

        # قیمت Variant تغییر می‌کند
        self.variant.price = Decimal("700000.00")
        self.variant.save(update_fields=["price"])

        item.refresh_from_db()

        # قیمت سفارش قبلی نباید تغییر کند
        self.assertEqual(
            item.unit_price,
            Decimal("500000.00"),
        )

        self.assertEqual(
            item.total_price,
            Decimal("1000000.00"),
        )

    def test_order_has_unique_order_number(self):
        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
            subtotal=Decimal("100000.00"),
            total=Decimal("100000.00"),
        )

        self.assertIsNotNone(order.order_number)
        self.assertTrue(
            order.order_number.startswith("NM-")
        )

        self.assertNotEqual(
            order.id,
            order.order_number,
        )

    def test_order_has_currency(self):
        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
            currency="IRR",
            subtotal=Decimal("100000.00"),
            total=Decimal("100000.00"),
        )

        self.assertEqual(
            order.currency,
            "IRR",
        )

    def test_order_has_address_snapshots(self):
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

        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
            subtotal=Decimal("100000.00"),
            total=Decimal("100000.00"),
            shipping_address=shipping_address,
            billing_address=billing_address,
        )

        self.assertEqual(
            order.shipping_address,
            shipping_address,
        )

        self.assertEqual(
            order.billing_address,
            billing_address,
        )

    def test_order_has_customer_note(self):
        order = Order.objects.create(
            shop=self.shop,
            user=self.user,
            subtotal=Decimal("100000.00"),
            total=Decimal("100000.00"),
            customer_note="Please deliver after 6 PM.",
        )

        self.assertEqual(
            order.customer_note,
            "Please deliver after 6 PM.",
        )

    def test_order_total_must_match_components(self):
        with self.assertRaises(Exception):
            Order.objects.create(
                shop=self.shop,
                user=self.user,
                subtotal=Decimal("1000000.00"),
                discount=Decimal("100000.00"),
                shipping_cost=Decimal("50000.00"),
                total=Decimal("123456.00"),
            )