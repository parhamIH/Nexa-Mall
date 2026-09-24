from dataclasses import dataclass


# The evaluation DATASET is deliberately independent of both the
# metric engine and the search engine: it only declares, per query,
# how relevant each item is. It says NOTHING about how search works,
# and it is NOT derived from what search currently returns - graded
# by business judgment (section 13 of the spec):
#
#   Search Score     !=  Relevance Score
#   (our prediction)     (human ground truth)
#
# Relevance model (section 1):
#   3 = Exact / Highly Relevant
#   2 = Strongly Relevant
#   1 = Weakly Relevant
#   0 = Irrelevant  (kept in the dataset for contrast; never counts
#                    as relevant for Precision/Recall - only > 0)
#
# Identifiers are product SLUGS (human-readable dataset; production
# monitoring may later switch to stable UUIDs). Every slug in the
# dataset MUST be owned by the fixture the benchmark runs against -
# a slug no fixture owns would silently measure nothing.
#
# A tuple is used instead of a dict because @dataclass(frozen=True)
# does NOT make an inner dict immutable: the dataset itself must be
# truly immutable.
#
# Workspace note: for "running shoes" a Nike Shirt is graded 0
# (explicitly irrelevant) while both brands' running shoes are 3 -
# this is exactly the graded contrast the binary set cannot express.


@dataclass(frozen=True)
class SearchEvaluationCase:
    query: str

    # slug -> relevance
    # 0 = irrelevant
    # 1 = weakly relevant
    # 2 = relevant
    # 3 = highly relevant
    relevance: tuple[tuple[str, int], ...]

    def relevance_map(self) -> dict[str, int]:
        return dict(self.relevance)

    def relevant_slugs(self) -> set[str]:
        return {
            slug
            for slug, score in self.relevance
            if score > 0
        }


SEARCH_EVALUATION_DATASET = (
    SearchEvaluationCase(
        query="nike air max",
        relevance=(
            ("nike-air-max-270", 3),
            ("nike-air-max-90", 2),
            ("nike-running-shoes", 1),
            ("adidas-air-shoes", 0),
        ),
    ),
    SearchEvaluationCase(
        query="nike",
        relevance=(
            ("nike-air-max-270", 3),
            ("nike-running-shoes", 3),
            ("nike-sports-shoes", 2),
            ("nike-shirt", 2),
            ("adidas-running-shoes", 0),
        ),
    ),
    SearchEvaluationCase(
        query="running shoes",
        relevance=(
            ("nike-running-shoes", 3),
            ("adidas-running-shoes", 3),
            ("nike-sports-shoes", 2),
            ("nike-casual-shoes", 1),
            ("nike-shirt", 0),
        ),
    ),
)