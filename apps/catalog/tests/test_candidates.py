from django.test import SimpleTestCase

from apps.catalog.search.candidates import (
    CandidateGenerator,
)


class CandidateGeneratorTests(SimpleTestCase):

    def test_candidates_are_deduplicated(self):
        def exact_fetcher(query, limit):
            return [1, 2, 3]

        def trigram_fetcher(query, limit):
            return [2, 3, 4]

        generator = CandidateGenerator(
            fetchers={
                "exact_name": exact_fetcher,
                "trigram": trigram_fetcher,
            },
            per_channel_limit=50,
        )

        result = generator.generate(
            "nike air max",
        )

        self.assertEqual(
            set(result.product_ids),
            {1, 2, 3, 4},
        )

    def test_channel_provenance_is_preserved(self):
        def exact_fetcher(query, limit):
            return [1, 2]

        def trigram_fetcher(query, limit):
            return [2, 3]

        generator = CandidateGenerator(
            fetchers={
                "exact_name": exact_fetcher,
                "trigram": trigram_fetcher,
            },
        )

        result = generator.generate(
            "nike",
        )

        candidates = {
            candidate.product_id: candidate.channels
            for candidate in result.candidates
        }

        self.assertEqual(
            candidates[1],
            frozenset({"exact_name"}),
        )

        self.assertEqual(
            candidates[2],
            frozenset({
                "exact_name",
                "trigram",
            }),
        )

        self.assertEqual(
            candidates[3],
            frozenset({"trigram"}),
        )

    def test_empty_query_returns_empty_candidate_set(self):
        generator = CandidateGenerator(
            fetchers={
                "exact_name": lambda query, limit: [1, 2],
            },
        )

        result = generator.generate("   ")

        self.assertEqual(
            result.product_ids,
            (),
        )