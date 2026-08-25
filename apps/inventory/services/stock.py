from django.db import transaction
from django.core.exceptions import ValidationError

from apps.inventory.models import InventoryItem, StockMovement


class StockService:

    @staticmethod
    @transaction.atomic
    def receive_stock(
        *,
        variant,
        quantity,
        reference="",
    ):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        inventory = (
            InventoryItem.objects
            .select_for_update()
            .get(variant=variant)
        )

        inventory.on_hand += quantity

        inventory.save(
            update_fields=[
                "on_hand",
                "updated_at",
            ]
        )

        StockMovement.objects.create(
            inventory=inventory,
            movement_type=StockMovement.Type.RECEIPT,
            quantity=quantity,
            reference=reference,
        )

        return inventory

    @staticmethod
    @transaction.atomic
    def reserve_stock(
        *,
        variant,
        quantity,
        reference="",
    ):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        inventory = (
            InventoryItem.objects
            .select_for_update()
            .get(variant=variant)
        )

        available = inventory.on_hand - inventory.reserved

        if available < quantity:
            raise ValidationError(
                f"Insufficient stock. "
                f"Available: {available}, Requested: {quantity}."
            )

        inventory.reserved += quantity

        inventory.save(
            update_fields=[
                "reserved",
                "updated_at",
            ]
        )

        StockMovement.objects.create(
            inventory=inventory,
            movement_type=StockMovement.Type.RESERVE,
            quantity=quantity,
            reference=reference,
        )

        return inventory
    
    @staticmethod
    @transaction.atomic
    def release_stock(
        *,
        variant,
        quantity,
        reference="",
    ):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        inventory = (
            InventoryItem.objects
            .select_for_update()
            .get(variant=variant)
        )

        if inventory.reserved < quantity:
            raise ValidationError(
                f"Cannot release {quantity} units. "
                f"Reserved: {inventory.reserved}."
            )

        inventory.reserved -= quantity

        inventory.save(
            update_fields=[
                "reserved",
                "updated_at",
            ]
        )

        StockMovement.objects.create(
            inventory=inventory,
            movement_type=StockMovement.Type.RELEASE,
            quantity=quantity,
            reference=reference,
        )

        return inventory

    @staticmethod
    @transaction.atomic
    def commit_sale(
        *,
        variant,
        quantity,
        reference="",
    ):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        inventory = (
            InventoryItem.objects
            .select_for_update()
            .get(variant=variant)
        )

        if inventory.reserved < quantity:
            raise ValidationError(
                f"Cannot commit sale. "
                f"Reserved: {inventory.reserved}."
            )

        if inventory.on_hand < quantity:
            raise ValidationError(
                f"Cannot commit sale. "
                f"On hand: {inventory.on_hand}."
            )

        inventory.on_hand -= quantity
        inventory.reserved -= quantity

        inventory.save(
            update_fields=[
                "on_hand",
                "reserved",
                "updated_at",
            ]
        )

        StockMovement.objects.create(
            inventory=inventory,
            movement_type=StockMovement.Type.SALE,
            quantity=quantity,
            reference=reference,
        )

        return inventory