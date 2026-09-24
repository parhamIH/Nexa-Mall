from dataclasses import dataclass
from typing import Callable

from .evaluation import (
    mean_reciprocal_rank,
    ndcg_at_k,
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


@dataclass(frozen=True)
class SearchBenchmarkResult:
    """
    Quality result over the (single, graded) evaluation dataset.

    The BINARY trio answers "did we find the relevant items?":
      - precision_at_5: of what we SHOWED, how much was relevant
      - recall_at_5:    of everything relevant, how much we FOUND
      - mrr:            how close to the top the first relevant item lands
    A grade-0 item (explicitly irrelevant) is never counted here:
    only grade > 0 counts as relevant.

    NDCG@5 is the RANKING metric the trio cannot see: an engine that
    returns every relevant item in the WORST order still scores
    perfectly on recall, but NDCG@5 punishes exactly that ordering.
    It is the headline ranking-quality number for the marketplace.
    """
    precision_at_5: float
    recall_at_5: float
    mrr: float
    ndcg_at_5: float


def run_search_benchmark(
    search: SearchFunction,
) -> SearchBenchmarkResult:
    """
    Run the evaluation dataset through `search` and aggregate the
    four metrics (macro average: every query weighs equally, which
    suits a small dataset - no single query dominates).

    Retrieval -> graded relevance is done HERE, not by the metric
    engine (section 5): the engine's raw sorted score list is
    mapped to ground-truth relevance via the per-query relevance
    map (missing slugs are 0), and the IDEAL is built from ALL
    graded values sorted descending - including grade-0 items that
    the engine MISSED entirely, so NDCG@5 penalizes losing relevant
    items, not just misordering the ones found (section 4).

    The dataset is fully GRADED (slug -> relevance grade): the
    binary metrics derive their relevance sets from the grades
    (grade > 0 counts as relevant), and NDCG@5 consumes the raw
    grades. One dataset, one source of truth.

    Deliberately no pass/fail thresholds here: thresholds belong to
    regression tests and only AFTER a real, validated baseline
    exists (30+ real queries) - locking numbers in early invites
    tuning the data to the test instead of the test protecting the
    quality.
    """
    retrieved_results: list[list[str]] = []
    relevant_sets: list[set[str]] = []

    precision_scores: list[float] = []
    recall_scores: list[float] = []
    ndcg_scores: list[float] = []

    k = 5

    for case in SEARCH_EVALUATION_DATASET:
        relevance_map = case.relevance_map()

        relevant = {
            slug
            for slug, score in relevance_map.items()
            if score > 0
        }

        if not relevant:
            continue

        retrieved = search(case.query)

        retrieved_relevance = [
            relevance_map.get(slug, 0)
            for slug in retrieved
        ]

        ideal_relevance = sorted(
            relevance_map.values(),
            reverse=True,
        )

        retrieved_results.append(retrieved)
        relevant_sets.append(relevant)

        precision_scores.append(
            precision_at_k(retrieved, relevant, k)
        )

        recall_scores.append(
            recall_at_k(retrieved, relevant, k)
        )

        ndcg_scores.append(
            ndcg_at_k(
                retrieved_relevance,
                ideal_relevance,
                k=k,
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

    ndcg_at_5 = (
        sum(ndcg_scores) / len(ndcg_scores)
        if ndcg_scores
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
        ndcg_at_5=ndcg_at_5,
    )