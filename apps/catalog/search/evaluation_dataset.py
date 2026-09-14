from dataclasses import dataclass


# The evaluation DATASET is intentionally separate from both the
# metric engine and the search engine: it only declares, per query,
# which items are RELEVANT - it says nothing about how search works.
#
# Identifiers are product SLUGS for now (human-readable dataset:
# "nike-air-max" beats "0d54c9f6-..."). Production monitoring may
# later switch to stable UUIDs.
#
# retrieved results: ORDER matters (it is a ranked list)
# relevant set:      order DOES NOT matter -> frozenset, and the
#                    dataset itself stays immutable.


@dataclass(frozen=True)
class SearchEvaluationCase:
    query: str
    relevant: frozenset[str]


SEARCH_EVALUATION_DATASET = (
    SearchEvaluationCase(
        query="nike air max",
        relevant=frozenset({
            "nike-air-max",
        }),
    ),
    SearchEvaluationCase(
        query="nike",
        relevant=frozenset({
            "nike-air-max",
            "nike-running",
            "nike-shirt",
        }),
    ),
    SearchEvaluationCase(
        query="running shoes",
        relevant=frozenset({
            "nike-air-max",
            "nike-running",
        }),
    ),
    SearchEvaluationCase(
        query="black shoes",
        relevant=frozenset({
            "black-running-shoes",
            "black-sneakers",
        }),
    ),
    SearchEvaluationCase(
        query="air max",
        relevant=frozenset({
            "nike-air-max",
        }),
    ),
    SearchEvaluationCase(
        query="nike air",
        relevant=frozenset({
            "nike-air-max",
        }),
    ),
)
