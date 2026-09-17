from django.core.management.base import BaseCommand

from apps.catalog.search.adapter import HybridSearchAdapter
from apps.catalog.search.benchmark import run_search_benchmark


class Command(BaseCommand):
    help = (
        "Run the Search Quality Benchmark against the REAL hybrid "
        "search ranking (the same filter the public API serves)."
    )

    def handle(self, *args, **options):
        adapter = HybridSearchAdapter()

        result = run_search_benchmark(
            adapter.search,
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Search Quality Benchmark"
            )
        )
        self.stdout.write("-" * 40)

        self.stdout.write(
            f"Precision@5 : {result.precision_at_5:.4f}"
        )

        self.stdout.write(
            f"Recall@5    : {result.recall_at_5:.4f}"
        )

        self.stdout.write(
            f"MRR         : {result.mrr:.4f}"
        )

        self.stdout.write(
            f"NDCG@5      : {result.ndcg_at_5:.4f}"
        )

        self.stdout.write("")
