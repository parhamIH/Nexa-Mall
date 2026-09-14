from django.db import connection
from django.test import TestCase

from apps.catalog.models import Product


class ProductFullTextIndexTests(TestCase):

    def test_product_full_text_index_exists(self):
        index_names = {
            index.name
            for index in Product._meta.indexes
        }

        self.assertIn(
            "product_fts_search_idx",
            index_names,
        )

    def test_product_full_text_index_exists_in_database(self):
        if connection.vendor != "postgresql":
            self.skipTest(
                "GIN FTS indexes are PostgreSQL-only."
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE indexname = 'product_fts_search_idx'
                """
            )

            row = cursor.fetchone()

        self.assertIsNotNone(
            row,
        )

        # The live index must carry the WEIGHTS: the filter ranks by
        # them, and a weightless vector would also mismatch the
        # query's expression so the planner could never use it.
        self.assertIn(
            "'A'",
            row[0],
        )

        self.assertIn(
            "'B'",
            row[0],
        )

        self.assertIn(
            "'D'",
            row[0],
        )
