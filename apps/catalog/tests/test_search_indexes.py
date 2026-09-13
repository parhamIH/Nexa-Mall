from django.db import connection
from django.test import TestCase

from apps.catalog.models import (
    Brand,
    Product,
    ProductVariant,
)


def is_postgres():
    return connection.vendor == "postgresql"


class SearchIndexTests(TestCase):
    """
    Model metadata assertions run on every database; the database
    introspection / extension tests are PostgreSQL-only (pg_trgm
    does not exist elsewhere).
    """

    def test_product_trigram_indexes_exist(self):
        indexes = {
            index.name
            for index in Product._meta.indexes
        }

        self.assertIn(
            "product_name_trgm_idx",
            indexes,
        )

        self.assertIn(
            "product_slug_trgm_idx",
            indexes,
        )

        self.assertIn(
            "product_desc_trgm_idx",
            indexes,
        )

    def test_variant_trigram_indexes_exist(self):
        indexes = {
            index.name
            for index in ProductVariant._meta.indexes
        }

        self.assertIn(
            "variant_sku_trgm_idx",
            indexes,
        )

        self.assertIn(
            "variant_name_trgm_idx",
            indexes,
        )

    def test_brand_trigram_index_exists(self):
        indexes = {
            index.name
            for index in Brand._meta.indexes
        }

        self.assertIn(
            "brand_name_trgm_idx",
            indexes,
        )


class PostgreSQLSearchExtensionTests(TestCase):

    def test_pg_trgm_is_installed(self):
        if not is_postgres():
            self.skipTest(
                "pg_trgm is PostgreSQL-only."
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM pg_extension
                WHERE extname = 'pg_trgm'
                """
            )

            result = cursor.fetchone()

        self.assertIsNotNone(
            result,
        )

    def test_trigram_indexes_exist_in_database(self):
        if not is_postgres():
            self.skipTest(
                "GIN trigram indexes are PostgreSQL-only."
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE indexname LIKE '%%trgm%%'
                ORDER BY indexname
                """
            )

            names = {
                row[0]
                for row in cursor.fetchall()
            }

        self.assertEqual(
            names,
            {
                "brand_name_trgm_idx",
                "product_name_trgm_idx",
                "product_slug_trgm_idx",
                "product_desc_trgm_idx",
                "variant_sku_trgm_idx",
                "variant_name_trgm_idx",
            },
        )
