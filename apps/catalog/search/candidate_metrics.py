from collections.abc import Collection, Iterable


def candidate_recall_at_k(
    candidate_ids: Iterable,
    relevant_ids: Collection,
) -> float:
    """
    Recall of the candidate pool.

    candidate_ids:
        Products entering the ranking stage.

    relevant_ids:
        Ground-truth relevant products.
    """
    relevant = set(relevant_ids)

    if not relevant:
        return 1.0

    candidates = set(candidate_ids)

    return len(candidates & relevant) / len(relevant)