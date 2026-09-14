from collections.abc import Iterable


# The evaluation engine is deliberately framework-free: it works on
# plain string IDs, not model instances. Search quality must be
# measurable independently of Django/ORM/database so the metrics are
# fast, portable and reusable (e.g. against a future OpenSearch
# engine with the same benchmark harness).
#
#   Search API -> ordered product IDs -> evaluation engine


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
