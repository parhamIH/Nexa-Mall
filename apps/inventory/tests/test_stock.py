from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import InventoryItem, StockMovement
from apps.inventory.services.stock import StockService
from apps.tenants.models import Shop, Tenant


class StockServiceTests(TestCase):

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
            name="Test Product",
            slug="test-product",
        )

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="TEST-001",
            price="100000",
        )

        cls.inventory = InventoryItem.objects.create(
            variant=cls.variant,
            on_hand=10,
            reserved=0,
        )

    def test_receive_stock(self):
        inventory = StockService.receive_stock(
            variant=self.variant,
            quantity=5,
            reference="receipt-001",
        )

        self.assertEqual(inventory.on_hand, 15)
        self.assertEqual(inventory.reserved, 0)

        self.assertTrue(
            StockMovement.objects.filter(
                inventory=inventory,
                movement_type=StockMovement.Type.RECEIPT,
                quantity=5,
            ).exists()
        )

    def test_reserve_stock(self):
        inventory = StockService.reserve_stock(
            variant=self.variant,
            quantity=4,
            reference="reservation-001",
        )

        self.assertEqual(inventory.on_hand, 10)
        self.assertEqual(inventory.reserved, 4)
        self.assertEqual(inventory.available, 6)

    def test_cannot_reserve_more_than_available(self):
        with self.assertRaises(ValidationError):
            StockService.reserve_stock(
                variant=self.variant,
                quantity=11,
                reference="reservation-002",
            )

    def test_release_stock(self):
        StockService.reserve_stock(
            variant=self.variant,
            quantity=4,
            reference="reservation-003",
        )

        inventory = StockService.release_stock(
            variant=self.variant,
            quantity=4,
            reference="release-001",
        )

        self.assertEqual(inventory.on_hand, 10)
        self.assertEqual(inventory.reserved, 0)

    def test_cannot_release_more_than_reserved(self):
        with self.assertRaises(ValidationError):
            StockService.release_stock(
                variant=self.variant,
                quantity=1,
                reference="release-002",
            )

    def test_commit_sale(self):
        StockService.reserve_stock(
            variant=self.variant,
            quantity=4,
            reference="reservation-004",
        )

        inventory = StockService.commit_sale(
            variant=self.variant,
            quantity=4,
            reference="sale-001",
        )

        self.assertEqual(inventory.on_hand, 6)
        self.assertEqual(inventory.reserved, 0)
        self.assertEqual(inventory.available, 6)