from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant
from apps.inventory.models import InventoryItem, Reservation, StockMovement
from apps.inventory.services.reservation import ReservationService
from apps.inventory.services.stock import StockService
from apps.tenants.models import Tenant, Shop


class ReservationServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # -------------------------
        # Tenant
        # -------------------------

        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
        )

        # -------------------------
        # Shop
        # -------------------------

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Test Shop",
            slug="test-shop",
        )

        # -------------------------
        # Product
        # -------------------------

        cls.product = Product.objects.create(
            shop=cls.shop,
            name="Test Product",
            slug="test-product",
            description="Test product",
            status=Product.Status.ACTIVE,
        )

        # -------------------------
        # Product Variant
        # -------------------------

        cls.variant = ProductVariant.objects.create(
            product=cls.product,
            sku="TEST-SKU-001",
            name="Test Variant",
            price=100,
            status=ProductVariant.Status.ACTIVE,
        )

        # -------------------------
        # Inventory
        # -------------------------

        cls.inventory = InventoryItem.objects.create(
            variant=cls.variant,
            on_hand=10,
            reserved=0,
        )

    # =========================================================
    # CREATE
    # =========================================================

    def test_create_reservation(self):
        expires_at = timezone.now() + timedelta(minutes=15)

        reservation = ReservationService.create_reservation(
            variant=self.variant,
            quantity=3,
            reference="RES-001",
            expires_at=expires_at,
        )

        self.assertEqual(
            reservation.status,
            Reservation.Status.ACTIVE,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.on_hand,
            10,
        )

        self.assertEqual(
            self.inventory.reserved,
            3,
        )

        self.assertEqual(
            self.inventory.available,
            7,
        )

        self.assertTrue(
            StockMovement.objects.filter(
                inventory=self.inventory,
                movement_type=StockMovement.Type.RESERVE,
                quantity=3,
                reference="RES-001",
            ).exists()
        )

    def test_create_reservation_with_insufficient_stock(self):
        expires_at = timezone.now() + timedelta(minutes=15)

        with self.assertRaises(ValidationError):
            ReservationService.create_reservation(
                variant=self.variant,
                quantity=11,
                reference="RES-INSUFFICIENT",
                expires_at=expires_at,
            )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.on_hand,
            10,
        )

        self.assertEqual(
            self.inventory.reserved,
            0,
        )

        self.assertFalse(
            Reservation.objects.filter(
                reference="RES-INSUFFICIENT",
            ).exists()
        )

    def test_create_reservation_with_invalid_quantity(self):
        expires_at = timezone.now() + timedelta(minutes=15)

        with self.assertRaises(ValueError):
            ReservationService.create_reservation(
                variant=self.variant,
                quantity=0,
                reference="RES-INVALID",
                expires_at=expires_at,
            )

    def test_create_reservation_with_expired_time(self):
        expires_at = timezone.now() - timedelta(minutes=1)

        with self.assertRaises(ValidationError):
            ReservationService.create_reservation(
                variant=self.variant,
                quantity=3,
                reference="RES-EXPIRED",
                expires_at=expires_at,
            )

    # =========================================================
    # CONFIRM
    # =========================================================

    def test_confirm_reservation(self):
        expires_at = timezone.now() + timedelta(minutes=15)

        reservation = ReservationService.create_reservation(
            variant=self.variant,
            quantity=3,
            reference="RES-002",
            expires_at=expires_at,
        )

        ReservationService.confirm_reservation(
            reservation=reservation,
        )

        reservation.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            reservation.status,
            Reservation.Status.CONFIRMED,
        )

        self.assertEqual(
            self.inventory.on_hand,
            7,
        )

        self.assertEqual(
            self.inventory.reserved,
            0,
        )

        self.assertEqual(
            self.inventory.available,
            7,
        )

        self.assertTrue(
            StockMovement.objects.filter(
                inventory=self.inventory,
                movement_type=StockMovement.Type.SALE,
                quantity=3,
                reference="RES-002",
            ).exists()
        )

    def test_cannot_confirm_expired_reservation(self):
        reservation = Reservation.objects.create(
            inventory=self.inventory,
            quantity=3,
            reference="RES-005",
            expires_at=timezone.now() - timedelta(minutes=1),
            status=Reservation.Status.ACTIVE,
        )

        self.inventory.reserved = 3
        self.inventory.save(
            update_fields=[
                "reserved",
                "updated_at",
            ]
        )

        with self.assertRaises(ValidationError):
            ReservationService.confirm_reservation(
                reservation=reservation,
            )

        reservation.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            reservation.status,
            Reservation.Status.ACTIVE,
        )

        self.assertEqual(
            self.inventory.on_hand,
            10,
        )

        self.assertEqual(
            self.inventory.reserved,
            3,
        )

    def test_cannot_confirm_released_reservation(self):
        reservation = Reservation.objects.create(
            inventory=self.inventory,
            quantity=3,
            reference="RES-006",
            expires_at=timezone.now() + timedelta(minutes=15),
            status=Reservation.Status.RELEASED,
        )

        with self.assertRaises(ValidationError):
            ReservationService.confirm_reservation(
                reservation=reservation,
            )

    # =========================================================
    # RELEASE
    # =========================================================

    def test_release_reservation(self):
        expires_at = timezone.now() + timedelta(minutes=15)

        reservation = ReservationService.create_reservation(
            variant=self.variant,
            quantity=3,
            reference="RES-003",
            expires_at=expires_at,
        )

        ReservationService.release_reservation(
            reservation=reservation,
        )

        reservation.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            reservation.status,
            Reservation.Status.RELEASED,
        )

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

        self.assertTrue(
            StockMovement.objects.filter(
                inventory=self.inventory,
                movement_type=StockMovement.Type.RELEASE,
                quantity=3,
                reference="RES-003",
            ).exists()
        )

    def test_cannot_release_released_reservation(self):
        reservation = Reservation.objects.create(
            inventory=self.inventory,
            quantity=3,
            reference="RES-007",
            expires_at=timezone.now() + timedelta(minutes=15),
            status=Reservation.Status.RELEASED,
        )

        with self.assertRaises(ValidationError):
            ReservationService.release_reservation(
                reservation=reservation,
            )

    # =========================================================
    # EXPIRE
    # =========================================================

    def test_expire_reservation(self):
        expires_at = timezone.now() - timedelta(minutes=1)

        reservation = Reservation.objects.create(
            inventory=self.inventory,
            quantity=3,
            reference="RES-004",
            expires_at=expires_at,
            status=Reservation.Status.ACTIVE,
        )

        StockService.reserve_stock(
            variant=self.variant,
            quantity=3,
            reference="RES-004",
        )

        ReservationService.expire_reservation(
            reservation=reservation,
        )

        reservation.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(
            reservation.status,
            Reservation.Status.EXPIRED,
        )

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

    def test_cannot_expire_active_reservation(self):
        reservation = Reservation.objects.create(
            inventory=self.inventory,
            quantity=3,
            reference="RES-008",
            expires_at=timezone.now() + timedelta(minutes=15),
            status=Reservation.Status.ACTIVE,
        )

        self.inventory.reserved = 3
        self.inventory.save(
            update_fields=[
                "reserved",
                "updated_at",
            ]
        )

        with self.assertRaises(ValidationError):
            ReservationService.expire_reservation(
                reservation=reservation,
            )