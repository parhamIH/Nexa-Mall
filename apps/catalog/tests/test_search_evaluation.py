import math

from django.test import SimpleTestCase

from apps.catalog.search.evaluation import (
    dcg_at_k,
    idcg_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


class SearchEvaluationTests(SimpleTestCase):
    """Binary relevance metrics (P@K, R@K, MRR): a result is either
    relevant or it is not."""

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


class SearchNdcgTests(SimpleTestCase):
    """Graded relevance via the SLUG-MAP convention: NDCG@K measures
    whether the best results are ranked first - the property binary
    P@K/R@K/MRR cannot see."""

    def test_dcg_at_k_single_result_first(self):
        # One grade-3 result at rank 1: full exponential gain, no
        # discount. gain(3) = 2**3 - 1 = 7.
        self.assertEqual(
            dcg_at_k([3, 0, 0], k=5),
            7.0,
        )

    def test_dcg_discounts_by_rank(self):
        # Same gain at rank 1 vs rank 3: rank 3 pays log2(4) = 2.0.
        first = dcg_at_k([3, 0, 0], k=5)
        buried = dcg_at_k([0, 0, 3], k=5)

        self.assertGreater(first, buried)

        self.assertAlmostEqual(
            buried,
            7.0 / math.log2(4),
        )

    def test_dcg_at_k_only_counts_top_k(self):
        # The 4th item (rank 4+) must not contribute at K=3.
        self.assertEqual(
            dcg_at_k([0, 0, 0, 3], k=3),
            dcg_at_k([0, 0, 0], k=3),
        )

    def test_dcg_at_k_zero_for_empty(self):
        self.assertEqual(
            dcg_at_k([], k=5),
            0.0,
        )

        self.assertEqual(
            dcg_at_k([3], k=0),
            0.0,
        )

        self.assertEqual(
            dcg_at_k([0, 0], k=5),
            0.0,
        )

    def test_idcg_sorts_by_descending_gain(self):
        # Ideal ordering puts the grade-3 first, grade-2 second,
        # grade-1 third, with exponential gains 7, 3, 1.
        grades = {"a": 1, "b": 3, "c": 2}

        expected = (
            7 / math.log2(2)      # rank 1: gain(3) = 7
            + 3 / math.log2(3)    # rank 2: gain(2) = 3
            + 1 / math.log2(4)    # rank 3: gain(1) = 1
        )

        self.assertAlmostEqual(
            idcg_at_k(grades, 5),
            expected,
        )

    def test_idcg_at_k_zero_for_empty(self):
        self.assertEqual(idcg_at_k({}, 5), 0.0)
        self.assertEqual(idcg_at_k({"a": 3}, 0), 0.0)

    def test_ndcg_perfect_ordering_is_one(self):
        # Retrieved exactly in ideal order: NDCG = 1.0.
        grades = {"a": 3, "b": 2, "c": 1}

        self.assertEqual(
            ndcg_at_k(["a", "b", "c"], grades=grades, k=5),
            1.0,
        )

    def test_ndcg_bad_ordering_punished(self):
        # Same relevant set, worst possible order: NDCG < 1.
        grades = {"a": 3, "b": 2, "c": 1}

        perfect = ndcg_at_k(["a", "b", "c"], grades=grades, k=5)
        reversed_order = ndcg_at_k(["c", "b", "a"], grades=grades, k=5)

        self.assertEqual(perfect, 1.0)
        self.assertLess(reversed_order, 1.0)
        self.assertGreater(reversed_order, 0.0)

    def test_ndcg_all_grades_zero_returns_zero(self):
        # All results grade 0: IDCG is 0, NDCG must not divide by
        # zero - nothing relevant, score 0.
        self.assertEqual(
            ndcg_at_k(
                ["a", "b", "c"],
                grades={"a": 0, "b": 0},
                k=5,
            ),
            0.0,
        )

    def test_ndcg_zero_when_no_relevant_retrieved(self):
        self.assertEqual(
            ndcg_at_k(
                ["x", "y", "z"],
                grades={"a": 3, "b": 2},
                k=5,
            ),
            0.0,
        )

    def test_ndcg_missing_item_counts_as_zero(self):
        # A retrieved item not in the graded map is irrelevant
        # (grade 0): it must contribute nothing, not crash - real
        # engines return plenty of items the judgment set never
        # mentions.
        irrelevant_first = ndcg_at_k(
            ["ghost", "a", "c"],
            grades={"a": 3, "c": 1},
            k=5,
        )

        irrelevant_last = ndcg_at_k(
            ["a", "c", "ghost"],
            grades={"a": 3, "c": 1},
            k=5,
        )

        # The irrelevant item pushed the relevant ones DOWN: that
        # order must score lower than the same items with the
        # irrelevant one last.
        self.assertLess(
            irrelevant_first,
            irrelevant_last,
        )


class NDCGEvaluationTests(SimpleTestCase):
    """Section 9 spec: the graded relevance tests for the Nexa Mall
    marketplace model, using raw relevance SCORES (with an optional
    externally supplied ideal ranking):

        DCG@K  = Sum (2**rel_i - 1) / log2(i + 1)
        NDCG@K = DCG@K / IDCG@K

    Exponential gain is the marketplace model: gain(3) = 7,
    gain(2) = 3, gain(1) = 1, gain(0) = 0 - burying a perfect match
    under a merely relevant item must cost far more than ordering
    two marginally relevant items."""

    def test_dcg(self):
        # DCG@3 over scores [3, 3, 2]:
        #   7/log2(2) + 7/log2(3) + 3/log2(4)
        score = dcg_at_k([3, 3, 2], k=3)

        self.assertAlmostEqual(
            score,
            7 / math.log2(2)
            + 7 / math.log2(3)
            + 3 / math.log2(4),
        )

    def test_perfect_ndcg_is_one(self):
        # Retrieved in ideal (non-increasing) order: NDCG is exactly
        # 1.0, whatever the grades and length.
        self.assertEqual(
            ndcg_at_k([3, 3, 2, 0], k=4),
            1.0,
        )

        self.assertEqual(
            ndcg_at_k([3, 2, 1], k=3),
            1.0,
        )

    def test_reordered_results_have_lower_ndcg(self):
        # The same grades in a worse order must score below the
        # ideal ordering (here supplied explicitly).
        ideal = [3, 3, 2, 0]
        reordered = [2, 0, 3, 3]

        self.assertEqual(
            ndcg_at_k(ideal, k=4),
            1.0,
        )

        self.assertLess(
            ndcg_at_k(reordered, k=4),
            ndcg_at_k(ideal, k=4),
        )

        self.assertGreater(
            ndcg_at_k(reordered, k=4),
            0.0,
        )

    def test_ndcg_is_zero_when_no_relevant_items_exist(self):
        # All grades 0: IDCG = 0 -> NDCG must return 0.0, never a
        # division error.
        self.assertEqual(
            ndcg_at_k([0, 0, 0], k=3),
            0.0,
        )

        self.assertEqual(
            ndcg_at_k([], k=5),
            0.0,
        )

    def test_explicit_ideal_relevance_scores(self):
        # When an external ground-truth ideal is supplied, it wins
        # over the self-derived ideal: a ranking that looks perfect
        # on its own must be measured against the judge's ideal.
        retrieved = [3, 2, 1]       # NDCG 1.0 by itself
        ideal = [3, 3, 3]           # but the judge's ideal is 3s

        self.assertLess(
            ndcg_at_k(
                retrieved,
                k=3,
                ideal_relevance_scores=ideal,
            ),
            1.0,
        )