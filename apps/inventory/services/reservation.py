from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import Reservation
from apps.inventory.services.stock import StockService


class ReservationService:

    @staticmethod
    @transaction.atomic
    def create_reservation(
        *,
        variant,
        quantity,
        reference,
        expires_at,
    ):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if expires_at <= timezone.now():
            raise ValidationError(
                "Reservation expiration must be in the future."
            )

        reservation = Reservation.objects.create(
            inventory=variant.inventory,
            quantity=quantity,
            reference=reference,
            expires_at=expires_at,
            status=Reservation.Status.ACTIVE,
        )

        try:
            StockService.reserve_stock(
                variant=variant,
                quantity=quantity,
                reference=reference,
            )
        except Exception:
            reservation.delete()
            raise

        return reservation

    @staticmethod
    @transaction.atomic
    def confirm_reservation(
        *,
        reservation,
    ):
        if reservation.status != Reservation.Status.ACTIVE:
            raise ValidationError(
                "Only active reservations can be confirmed."
            )

        if reservation.expires_at <= timezone.now():
            raise ValidationError(
                "Reservation has expired."
            )

        StockService.commit_sale(
            variant=reservation.inventory.variant,
            quantity=reservation.quantity,
            reference=reservation.reference,
        )

        reservation.status = Reservation.Status.CONFIRMED
        reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return reservation

    @staticmethod
    @transaction.atomic
    def release_reservation(
        *,
        reservation,
    ):
        if reservation.status != Reservation.Status.ACTIVE:
            raise ValidationError(
                "Only active reservations can be released."
            )

        StockService.release_stock(
            variant=reservation.inventory.variant,
            quantity=reservation.quantity,
            reference=reservation.reference,
        )

        reservation.status = Reservation.Status.RELEASED
        reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return reservation

    @staticmethod
    @transaction.atomic
    def expire_reservation(
        *,
        reservation,
    ):
        if reservation.status != Reservation.Status.ACTIVE:
            raise ValidationError(
                "Only active reservations can expire."
            )

        if reservation.expires_at > timezone.now():
            raise ValidationError(
                "Reservation has not expired yet."
            )

        StockService.release_stock(
            variant=reservation.inventory.variant,
            quantity=reservation.quantity,
            reference=reservation.reference,
        )

        reservation.status = Reservation.Status.EXPIRED
        reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return reservation