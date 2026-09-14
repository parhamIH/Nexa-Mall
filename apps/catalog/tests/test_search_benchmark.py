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

        self.assertLessEqual(result.precision_at_5, 1)
        self.assertLessEqual(result.recall_at_5, 1)
        self.assertLessEqual(result.mrr, 1)

    def test_benchmark_with_perfect_search(self):
        # A search returning exactly the relevant set, best result
        # first, for every query: the benchmark must top out.
        from apps.catalog.search.evaluation_dataset import (
            SEARCH_EVALUATION_DATASET,
        )

        def perfect_search(query: str) -> list[str]:
            for case in SEARCH_EVALUATION_DATASET:
                if case.query == query:
                    return list(case.relevant)

            return []

        result = run_search_benchmark(perfect_search)

        self.assertEqual(result.precision_at_5, 1.0)
        self.assertEqual(result.recall_at_5, 1.0)
        self.assertEqual(result.mrr, 1.0)

    def test_benchmark_with_useless_search(self):
        # Nothing relevant ever retrieved: all metrics bottom out.
        def useless_search(query: str) -> list[str]:
            return [
                "adidas-shoe",
                "puma-socks",
            ]

        result = run_search_benchmark(useless_search)

        self.assertEqual(result.precision_at_5, 0.0)
        self.assertEqual(result.recall_at_5, 0.0)
        self.assertEqual(result.mrr, 0.0)
