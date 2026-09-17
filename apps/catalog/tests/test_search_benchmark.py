from django.test import SimpleTestCase

from apps.catalog.search.benchmark import run_search_benchmark


class SearchBenchmarkTests(SimpleTestCase):

    def test_benchmark_with_fake_search(self):
        # The fake search is a dependency stand-in: it proves the
        # benchmark wiring end to end (dataset -> callable ->
        # metrics -> aggregation) without a database. Wiring the
        # REAL hybrid search in comes next, replacing this fake.
        def fake_search(query: str) -> list[str]:
            results = {
                "nike air max": [
                    "nike-air-max",
                    "nike-running",
                    "nike-shirt",
                ],
                "nike": [
                    "nike-air-max",
                    "nike-running",
                    "nike-shirt",
                    "adidas-shoe",
                ],
                "running shoes": [
                    "nike-running",
                    "nike-air-max",
                    "black-running-shoes",
                ],
                "black shoes": [
                    "black-running-shoes",
                    "black-sneakers",
                    "nike-shirt",
                ],
                "air max": [
                    "nike-air-max",
                    "nike-running",
                ],
                "nike air": [
                    "nike-air-max",
                    "nike-running",
                ],
            }

            return results.get(query, [])

        result = run_search_benchmark(fake_search)

        self.assertGreater(result.precision_at_5, 0)
        self.assertGreater(result.recall_at_5, 0)
        self.assertGreater(result.mrr, 0)
        # The fake search ranks the graded top items first in most
        # queries; NDCG@5 must be a valid ratio, never NaN.
        self.assertGreater(result.ndcg_at_5, 0)

        self.assertLessEqual(result.precision_at_5, 1)
        self.assertLessEqual(result.recall_at_5, 1)
        self.assertLessEqual(result.mrr, 1)
        self.assertLessEqual(result.ndcg_at_5, 1)

    def test_benchmark_with_perfect_search(self):
        # A search returning exactly the RELEVANT items (grade > 0),
        # best result first, for every query: the benchmark must top
        # out on every metric including NDCG@5. Grade-0 judgments
        # stay out of the answer - the engine must not surface what
        # was judged explicitly irrelevant.
        from apps.catalog.search.evaluation_dataset import (
            SEARCH_EVALUATION_DATASET,
        )

        def perfect_search(query: str) -> list[str]:
            for case in SEARCH_EVALUATION_DATASET:
                if case.query == query:
                    return [
                        slug
                        for slug, grade in sorted(
                            case.relevance,
                            key=lambda item: item[1],
                            reverse=True,
                        )
                        if grade > 0
                    ]

            return []

        result = run_search_benchmark(perfect_search)

        self.assertEqual(result.precision_at_5, 1.0)
        self.assertEqual(result.recall_at_5, 1.0)
        self.assertEqual(result.mrr, 1.0)
        self.assertEqual(result.ndcg_at_5, 1.0)

    def test_benchmark_with_reversed_graded_search(self):
        # The SAME relevant items (grade > 0) in the WORST order:
        # binary metrics stay perfect, NDCG@5 must punish the
        # ordering - this is exactly the blindness the graded metric
        # fixes.
        from apps.catalog.search.evaluation_dataset import (
            SEARCH_EVALUATION_DATASET,
        )

        def reversed_search(query: str) -> list[str]:
            for case in SEARCH_EVALUATION_DATASET:
                if case.query == query:
                    return [
                        slug
                        for slug, grade in sorted(
                            case.relevance,
                            key=lambda item: item[1],
                            reverse=False,
                        )
                        if grade > 0
                    ]

            return []

        result = run_search_benchmark(reversed_search)

        self.assertEqual(result.precision_at_5, 1.0)
        self.assertEqual(result.recall_at_5, 1.0)
        self.assertEqual(result.mrr, 1.0)

        self.assertLess(result.ndcg_at_5, 1.0)
        self.assertGreater(result.ndcg_at_5, 0.0)

    def test_benchmark_with_useless_search(self):
        # Nothing relevant ever retrieved: all metrics bottom out.
        # The fake noise must be COMPLETELY unjudged - a slug with a
        # grade anywhere in the dataset would lift NDCG above zero
        # for that query.
        def useless_search(query: str) -> list[str]:
            return [
                "totally-unrelated",
                "also-unrelated",
            ]

        result = run_search_benchmark(useless_search)

        self.assertEqual(result.precision_at_5, 0.0)
        self.assertEqual(result.recall_at_5, 0.0)
        self.assertEqual(result.mrr, 0.0)
        self.assertEqual(result.ndcg_at_5, 0.0)

    def test_benchmark_skips_empty_relevance_cases(self):
        # The deliberate no-result query declares no judgments; the
        # benchmark must skip it rather than tax it or crash.
        from apps.catalog.search.evaluation_dataset import (
            SEARCH_EVALUATION_DATASET,
        )

        calls: list[str] = []

        def recording_search(query: str) -> list[str]:
            calls.append(query)
            return []

        run_search_benchmark(recording_search)

        self.assertNotIn("xyzabc123", calls)

        # Every non-skipped case was actually searched.
        for case in SEARCH_EVALUATION_DATASET:
            if case.relevant_slugs:
                self.assertIn(case.query, calls)