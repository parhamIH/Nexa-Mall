from dataclasses import dataclass
from typing import Callable

from .evaluation import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)
from .evaluation_dataset import SEARCH_EVALUATION_DATASET


# The search engine is a DEPENDENCY injected as a plain callable:
# the benchmark does not know (or care) whether results come from
# the Django ORM, PostgreSQL, an API or a future OpenSearch engine.
# This keeps search quality measurable independently of transport
# and API contracts (the DRF layer and the benchmark both consume
# the same search logic).

SearchFunction = Callable[[str], list[str]]

BENCHMARK_K = 5


@dataclass(frozen=True)
class SearchBenchmarkResult:
    precision_at_5: float
    recall_at_5: float
    mrr: float


def run_search_benchmark(
    search: SearchFunction,
) -> SearchBenchmarkResult:
    """
    Run the evaluation dataset through `search` and aggregate the
    three metrics.

    Precision@5 / Recall@5 are MACRO averaged (per query, then mean
    across queries): every query weighs equally, which suits a
    small dataset; no query dominates the benchmark.

    Deliberately no pass/fail thresholds here: thresholds belong to
    regression tests and only AFTER a real, validated baseline
    exists - locking numbers in early invites tuning the data to
    the test instead of the test protecting the quality.
    """
    retrieved_results: list[list[str]] = []
    relevant_sets: list[set[str]] = []

    precision_scores: list[float] = []
    recall_scores: list[float] = []

    for case in SEARCH_EVALUATION_DATASET:
        retrieved = search(case.query)

        retrieved_results.append(retrieved)
        relevant_sets.append(set(case.relevant))

        precision_scores.append(
            precision_at_k(
                retrieved,
                set(case.relevant),
                BENCHMARK_K,
            )
        )

        recall_scores.append(
            recall_at_k(
                retrieved,
                set(case.relevant),
                BENCHMARK_K,
            )
        )

    precision_at_5 = (
        sum(precision_scores) / len(precision_scores)
        if precision_scores
        else 0.0
    )

    recall_at_5 = (
        sum(recall_scores) / len(recall_scores)
        if recall_scores
        else 0.0
    )

    mrr = mean_reciprocal_rank(
        retrieved_results,
        relevant_sets,
    )

    return SearchBenchmarkResult(
        precision_at_5=precision_at_5,
        recall_at_5=recall_at_5,
        mrr=mrr,
    )
