from django.test import SimpleTestCase

from apps.catalog.search.evaluation import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


class SearchEvaluationTests(SimpleTestCase):

    def test_precision_at_k(self):
        retrieved = [
            "a",
            "b",
            "c",
            "d",
        ]

        relevant = {
            "a",
            "c",
        }

        self.assertEqual(
            precision_at_k(
                retrieved,
                relevant,
                3,
            ),
            2 / 3,
        )

    def test_precision_at_k_short_retrieval(self):
        # Only 3 results exist while K=10: dividing by the number of
        # results actually shown (3), not by K, must not punish the
        # engine for results it could not show.
        retrieved = [
            "a",
            "b",
            "c",
        ]

        relevant = {
            "a",
            "c",
        }

        self.assertEqual(
            precision_at_k(
                retrieved,
                relevant,
                10,
            ),
            2 / 3,
        )

    def test_recall_at_k(self):
        retrieved = [
            "a",
            "b",
            "c",
        ]

        relevant = {
            "a",
            "c",
            "d",
            "e",
        }

        self.assertEqual(
            recall_at_k(
                retrieved,
                relevant,
                3,
            ),
            2 / 4,
        )

    def test_reciprocal_rank(self):
        retrieved = [
            "x",
            "y",
            "target",
            "z",
        ]

        relevant = {
            "target",
        }

        self.assertEqual(
            reciprocal_rank(
                retrieved,
                relevant,
            ),
            1 / 3,
        )

    def test_reciprocal_rank_when_no_result_is_relevant(self):
        retrieved = [
            "a",
            "b",
            "c",
        ]

        relevant = {
            "target",
        }

        self.assertEqual(
            reciprocal_rank(
                retrieved,
                relevant,
            ),
            0.0,
        )

    def test_mean_reciprocal_rank(self):
        results = [
            ["target-a", "x", "y"],
            ["x", "target-b", "y"],
            ["x", "y", "target-c"],
        ]

        relevant_sets = [
            {"target-a"},
            {"target-b"},
            {"target-c"},
        ]

        expected = (
            1
            + (1 / 2)
            + (1 / 3)
        ) / 3

        self.assertEqual(
            mean_reciprocal_rank(
                results,
                relevant_sets,
            ),
            expected,
        )

    def test_empty_inputs(self):
        self.assertEqual(
            precision_at_k([], set(), 5),
            0.0,
        )

        self.assertEqual(
            recall_at_k([], set(), 5),
            0.0,
        )

        self.assertEqual(
            reciprocal_rank([], set()),
            0.0,
        )

        self.assertEqual(
            mean_reciprocal_rank([], []),
            0.0,
        )
