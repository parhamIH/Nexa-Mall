from collections.abc import Iterable, Mapping
from math import log2


# The evaluation engine is deliberately framework-free: it works on
# plain string IDs, not model instances. Search quality must be
# measurable independently of Django/ORM/database so the metrics are
# fast, portable and reusable (e.g. against a future OpenSearch
# engine with the same benchmark harness).
#
#   Search API -> ordered product IDs -> evaluation engine
#
# Two relevance models coexist here:
# - BINARY relevance (set of relevant IDs): P@K, R@K, MRR. A result
#   is either relevant or it is not.
# - GRADED relevance (mapping id -> relevance grade): NDCG@K. In a
#   marketplace, not everything relevant is EQUALLY relevant: for
#   "running shoes" a Nike Running Shoe (grade 3) is more relevant
#   than a Lite sports sock (grade 1). NDCG rewards putting the
#   HIGHER-graded results higher - it is the ranking-quality metric
#   the binary trio cannot see (a list is "all relevant" yet badly
#   ordered). Higher grades = more relevant.
#
# NDCG uses EXPONENTIAL gain (2**rel - 1), the marketplace model:
# the jump from "relevant" (2) to "exactly what I wanted" (3) must
# weigh far more than the jump from "marginally relevant" (1) to
# "relevant" (2):
#     gain(3) = 7, gain(2) = 3, gain(1) = 1
# Linear gain (relevance itself) would treat those jumps as equal,
# which understates how much a buried perfect match costs a shop.


def precision_at_k(
    retrieved: Iterable[str],
    relevant: set[str],
    k: int,
) -> float:
    """
    Precision@K = relevant items in the top K / K.

    Answers: "what fraction of what we SHOWED was relevant?"

    Divided by len(top-K retrieved), not by K itself: if the engine
    only returned 3 results and K=10, being unable to show 7 more
    results must not count as showing 7 irrelevant ones (a
    conventional choice, not an absolute rule).
    """
    if k <= 0:
        return 0.0

    retrieved_at_k = list(retrieved)[:k]

    if not retrieved_at_k:
        return 0.0

    relevant_count = sum(
        1
        for item in retrieved_at_k
        if item in relevant
    )

    return relevant_count / len(retrieved_at_k)


def recall_at_k(
    retrieved: Iterable[str],
    relevant: set[str],
    k: int,
) -> float:
    """
    Recall@K = relevant items retrieved in top K / total relevant.

    Answers: "what fraction of everything relevant did we FIND?"
    """
    if k <= 0 or not relevant:
        return 0.0

    retrieved_at_k = list(retrieved)[:k]

    relevant_count = sum(
        1
        for item in retrieved_at_k
        if item in relevant
    )

    return relevant_count / len(relevant)


def reciprocal_rank(
    retrieved: Iterable[str],
    relevant: set[str],
) -> float:
    """
    Reciprocal rank of the FIRST relevant result:
    rank 1 -> 1.0, rank 2 -> 0.5, rank 3 -> 0.333, ...
    """
    for position, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1 / position

    return 0.0


def mean_reciprocal_rank(
    results: Iterable[Iterable[str]],
    relevant_sets: Iterable[set[str]],
) -> float:
    """
    Mean Reciprocal Rank across multiple queries: on average, how
    close to the top does the first relevant result land?

    strict zip: a misaligned benchmark dataset (more queries than
    relevance judgments, or vice versa) must fail loudly, not
    silently drop queries.
    """
    reciprocal_ranks = [
        reciprocal_rank(retrieved, relevant)
        for retrieved, relevant in zip(
            results,
            relevant_sets,
            strict=True,
        )
    ]

    if not reciprocal_ranks:
        return 0.0

    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def _exponential_gain(relevance: float) -> float:
    """Marketplace relevance gain: 2**rel - 1 (gain 3 -> 7, 2 -> 3,
    1 -> 1, 0 -> 0). The gap between grades grows exponentially, so
    ranking a perfect match above a merely relevant item matters far
    more than ordering two marginally relevant items."""
    return 2 ** relevance - 1


def dcg_at_k(
    relevance_scores: Iterable[float],
    k: int,
) -> float:
    """
    Discounted Cumulative Gain at K with EXPONENTIAL gain: the
    graded relevance accumulated in the top K, discounted by rank.

        DCG@K = Σ (2**rel_i - 1) / log2(i + 1)

    Rank discount: rank 1 is undiscounted (log2(2) = 1), rank 2
    -> /1.58, rank 4 -> /2.32... A highly relevant result buried at
    rank 4 contributes less than the same result at rank 1, so a
    ranking that puts the BEST result first scores higher.
    """
    if k <= 0:
        return 0.0

    scores = list(relevance_scores)[:k]

    if not scores:
        return 0.0

    return sum(
        _exponential_gain(relevance) / log2(position + 1)
        for position, relevance in enumerate(
            scores,
            start=1,
        )
    )


def idcg_at_k(
    grades: Mapping[str, float],
    k: int,
) -> float:
    """
    Ideal DCG at K: the best possible DCG for this graded judgment
    set - the gains sorted by descending relevance, discounted by
    rank. The ceiling the retrieved ranking is measured against.
    """
    sorted_grades = sorted(
        grades.values(),
        reverse=True,
    )[:k]

    return sum(
        _exponential_gain(gain) / log2(position + 1)
        for position, gain in enumerate(
            sorted_grades,
            start=1,
        )
    )


def ndcg_at_k(
    retrieved: Iterable[str],
    grades: Mapping[str, float] | None = None,
    k: int = 5,
    ideal_relevance_scores: Iterable[float] | None = None,
) -> float:
    """
    Normalized DCG at K: how close the retrieved ranking comes to
    the ideal one, as a fraction in [0, 1].

    NDCG = DCG@K / IDCG@K. It is scale-free and position-aware -
    the metric the binary P@K/R@K/MRR trio cannot see. 1.0 means
    the perfect ordering (all relevant results, best first); 0.0
    means nothing relevant retrieved.

    Two calling conventions, exactly like the chapter describes:

    1. Retrieved SLUGS + a graded relevance MAP:
           ndcg_at_k(["a", "b"], {"a": 3, "b": 1}, k=5)
       Missing slugs are irrelevant (grade 0). The ideal ordering
       is derived from the map's own grades - the dataset IS the
       ground truth.

    2. Raw relevance SCORES, with an optional explicit ideal:
           ndcg_at_k([0, 2, 3, 3], k=4)
           ndcg_at_k([0, 2, 3], [3, 3, 2], k=5)
       When ideal_relevance_scores is None the ideal is the scores
       sorted descending (the best possible self-ordering); when
       given, an externally defined ground-truth ordering wins.
    """
    if k <= 0:
        return 0.0

    if grades is not None:
        # Convention 1: retrieved items -> relevance via the map.
        scores = [
            grades.get(item, 0.0)
            for item in retrieved
        ][:k]

        ideal_scores = sorted(
            grades.values(),
            reverse=True,
        )[:k]
    else:
        # Convention 2: raw relevance scores.
        scores = list(retrieved)[:k]

        if ideal_relevance_scores is None:
            ideal_scores = sorted(
                scores,
                reverse=True,
            )[:k]
        else:
            ideal_scores = list(
                ideal_relevance_scores
            )[:k]

    dcg = dcg_at_k(scores, k)
    idcg = dcg_at_k(ideal_scores, k)

    if idcg == 0:
        return 0.0

    return dcg / idcg
