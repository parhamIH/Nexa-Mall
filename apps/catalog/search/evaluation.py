from collections.abc import Iterable
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


def dcg_at_k(
    relevance_scores: Iterable[float],
    k: int,
) -> float:
    """
    Calculate Discounted Cumulative Gain at K using EXPONENTIAL
    gain (section 3):

        DCG@K = Σ (2**rel_i - 1) / log2(i + 1)

    Exponential gain is the marketplace model: the jump from
    "relevant" (2) to "exactly what I wanted" (3) must weigh far
    more than the jump from "weakly relevant" (1) to "relevant" (2):
        gain(3) = 7, gain(2) = 3, gain(1) = 1, gain(0) = 0

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
        (
            (2 ** relevance - 1)
            / log2(position + 1)
        )
        for position, relevance in enumerate(
            scores,
            start=1,
        )
    )


def ndcg_at_k(
    relevance_scores: Iterable[float],
    ideal_relevance_scores: Iterable[float] | None = None,
    k: int = 5,
) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain at K.

    NDCG = DCG@K / IDCG@K, a fraction in [0, 1]: how close the
    retrieved ranking comes to the ideal one. It is scale-free,
    position-aware, and normalized - the metric the binary
    P@K/R@K/MRR trio cannot see (section 1 / section 10):
      1.0 = perfect ranking (all relevant, best first)
      0.0 = nothing relevant retrieved

    The IDEAL must include ALL relevant grades, not just the ones
    the search found (section 4): if the ground truth is
    [3, 3, 2, 1] but search only found A and D, the ideal is
    [3, 3, 2, 1], NOT [3, 1] - otherwise NDCG would ignore the
    relevant items the engine MISSED. Only comparing against the
    full ideal makes NDCG reflect both ranking quality AND
    relevant-item loss.

    `ideal_relevance_scores` is optional for convenience (section
    8 of the NDCG chapter): when omitted, the ideal is the actual
    scores sorted descending - the best possible self-ordering.
    When supplied, an externally defined ground-truth ordering
    wins, which is what the benchmark passes.
    """
    if k <= 0:
        return 0.0

    actual = list(relevance_scores)[:k]

    if ideal_relevance_scores is None:
        ideal = sorted(
            actual,
            reverse=True,
        )[:k]
    else:
        ideal = list(
            ideal_relevance_scores
        )[:k]

    dcg = dcg_at_k(
        actual,
        k,
    )

    idcg = dcg_at_k(
        ideal,
        k,
    )

    if idcg == 0:
        return 0.0

    return dcg / idcg
