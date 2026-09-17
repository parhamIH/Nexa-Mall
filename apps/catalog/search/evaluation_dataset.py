from dataclasses import dataclass


# The evaluation DATASET is intentionally separate from both the
# metric engine and the search engine: it only declares, per query,
# which items are RELEVANT (and HOW relevant) - it says nothing
# about how search works.
#
# Identifiers are product SLUGS for now (human-readable dataset:
# "nike-air-max" beats "0d54c9f6-..."). Production monitoring may
# later switch to stable UUIDs.
#
# Since the NDCG chapter the dataset is fully GRADED: every case
# carries a relevance SCORE per item, not a flat in/out set.
#   - remove the binary `relevant` frozenset entirely; the binary
#     views (P@K, R@K, MRR) are DERIVED from the grades (grade > 0
#     counts as relevant), so there is a single source of truth.
#
# retrieved results: ORDER matters (it is a ranked list)
# relevance:         a mapping slug -> grade (grade 0 = explicitly
#                    irrelevant, kept for contrast; the dataset
#                    stays immutable).
#
# Every case also declares a QUERY TYPE so the dataset doubles as a
# coverage matrix: a search engine can be strong on exact names but
# blind to SKUs, and the matrix is what exposes that (see
# test_search_query_coverage.py).
#
# Grade scale (marketplace semantics):
#   3 = exactly what the query is about
#   2 = clearly relevant (same type of product)
#   1 = marginally relevant (same category, not the target)
#   0 = not relevant (present only when needed for contrast)


@dataclass(frozen=True)
class SearchEvaluationCase:
    query: str
    relevance: tuple[tuple[str, int], ...] = ()
    query_type: str = "general"

    @property
    def relevant_slugs(self) -> frozenset[str]:
        """Binary view of the graded judgments, for P@K / R@K / MRR:
        a slug is relevant when its grade is > 0. Grade 0 means
        "explicitly irrelevant" - it is kept in the dataset for
        contrast but never counts as relevant."""
        return frozenset(
            slug
            for slug, grade in self.relevance
            if grade > 0
        )

    @property
    def grades(self) -> dict[str, int]:
        """Slug -> grade mapping, for NDCG@K."""
        return dict(self.relevance)


SEARCH_EVALUATION_DATASET = (
    # Exact product name: the strongest, most unambiguous signal.
    SearchEvaluationCase(
        query="nike air max",
        relevance=(
            ("nike-air-max", 3),
        ),
        query_type="exact",
    ),
    # Brand-only query: every product of the brand is relevant; the
    # shirt is clearly related (2) but not the target.
    SearchEvaluationCase(
        query="nike",
        relevance=(
            ("nike-air-max", 3),
            ("nike-running", 3),
            ("nike-shirt", 2),
        ),
        query_type="brand",
    ),
    # Category-ish multi-word query: relevant across brands; the
    # vague cross-brand shoe is only marginally relevant (1).
    SearchEvaluationCase(
        query="running shoes",
        relevance=(
            ("nike-running", 3),
            ("nike-air-max", 3),
            ("adidas-shoe", 1),
        ),
        query_type="multi-word",
    ),
    # Partial name / substring target; a grade-0 item shows the
    # contrast scale: a branded shirt is EXPLICITLY not relevant.
    SearchEvaluationCase(
        query="black shoes",
        relevance=(
            ("black-running-shoes", 3),
            ("black-sneakers", 3),
            ("nike-shirt", 0),
        ),
        query_type="partial",
    ),
    # Short query: two tokens of the name, still a strong anchor.
    SearchEvaluationCase(
        query="air max",
        relevance=(
            ("nike-air-max", 3),
        ),
        query_type="short",
    ),
    SearchEvaluationCase(
        query="nike air",
        relevance=(
            ("nike-air-max", 3),
            ("nike-running", 2),
        ),
        query_type="multi-word",
    ),
    # Deliberate typo: must still retrieve via trigram similarity.
    SearchEvaluationCase(
        query="nkie air max",
        relevance=(
            ("nike-air-max", 3),
        ),
        query_type="typo",
    ),
    # Exact SKU: variant-level identifier, ranked by the SKU signal.
    # The SKU matches the fixture the benchmark runs against
    # (HybridSearchAdapterIntegrationTests), so this case actually
    # measures the SKU channel - a dataset naming a SKU no fixture
    # owns would silently measure nothing.
    SearchEvaluationCase(
        query="NIKE-AIR-MAX-001",
        relevance=(
            ("nike-air-max", 3),
        ),
        query_type="sku",
    ),
    # No-result / out-of-catalog query: the engine must not explode
    # and must not rank noise. Declares NO judgments (empty
    # relevance), so the benchmark skips it: a ranking metric over
    # an empty judgment set would be meaningless.
    SearchEvaluationCase(
        query="xyzabc123",
        relevance=(),
        query_type="no-result",
    ),
)