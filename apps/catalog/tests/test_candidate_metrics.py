from django.test import SimpleTestCase

from apps.catalog.search.candidate_metrics import (
    candidate_recall_at_k,
)


class CandidateRecallTests(SimpleTestCase):

    def test_all_relevant_products_are_candidates(self):
        result = candidate_recall_at_k(
            candidate_ids=[1, 2, 3, 4],
            relevant_ids={2, 4},
        )

        self.assertEqual(
            result,
            1.0,
        )

    def test_partial_candidate_recall(self):
        result = candidate_recall_at_k(
            candidate_ids=[1, 2, 3],
            relevant_ids={2, 4},
        )

        self.assertEqual(
            result,
            0.5,
        )

    def test_no_relevant_products(self):
        result = candidate_recall_at_k(
            candidate_ids=[1, 2, 3],
            relevant_ids=set(),
        )

        self.assertEqual(
            result,
            1.0,
        )