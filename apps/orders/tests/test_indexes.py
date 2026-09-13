from django.db import connection
from django.test import TestCase

from apps.orders.models import Order


class OrderIndexTests(TestCase):

    def test_order_listing_indexes_exist(self):
        index_names = {
            index.name
            for index in Order._meta.indexes
        }

        self.assertIn(
            "order_user_created_id_idx",
            index_names,
        )

        self.assertIn(
            "order_shop_created_id_idx",
            index_names,
        )

    def test_old_two_column_listing_indexes_are_gone(self):
        # The refined three-column indexes REPLACE the earlier
        # two-column ones for the same workload; keeping both
        # would double the index maintenance cost per order INSERT.
        field_sets = {
            tuple(index.fields)
            for index in Order._meta.indexes
        }

        self.assertNotIn(
            ("user", "created_at"),
            field_sets,
        )

        self.assertNotIn(
            ("shop", "created_at"),
            field_sets,
        )


class OrderDatabaseIndexTests(TestCase):
    """
    Model metadata says nothing about the real database: assert
    the migration actually created the indexes.
    """

    def test_order_indexes_exist_in_database(self):
        with connection.cursor() as cursor:
            constraints = (
                connection.introspection.get_constraints(
                    cursor,
                    Order._meta.db_table,
                )
            )

        self.assertIn(
            "order_user_created_id_idx",
            constraints,
        )

        self.assertIn(
            "order_shop_created_id_idx",
            constraints,
        )

    def test_old_listing_indexes_are_gone_from_database(self):
        with connection.cursor() as cursor:
            constraints = (
                connection.introspection.get_constraints(
                    cursor,
                    Order._meta.db_table,
                )
            )

        # The auto-generated names of the previous two-column
        # indexes are verified absent: replaced, not duplicated.
        old_names = [
            name
            for name in constraints
            if "user_id" in name
            or "shop_id" in name
        ]

        for name in old_names:
            columns = tuple(
                constraints[name].get(
                    "columns",
                    [],
                )
            )

            self.assertNotEqual(
                columns,
                ("user_id", "created_at"),
            )

            self.assertNotEqual(
                columns,
                ("shop_id", "created_at"),
            )
