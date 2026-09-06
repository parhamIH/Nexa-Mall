from django.test import TestCase

from apps.api.pagination import StandardPagination


class StandardPaginationTests(TestCase):

    def test_page_size_is_limited(self):
        pagination = StandardPagination()

        self.assertEqual(
            pagination.page_size,
            20,
        )

        self.assertEqual(
            pagination.max_page_size,
            100,
        )