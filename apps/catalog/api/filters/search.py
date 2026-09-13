from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import FloatField, Max, Value
from django.db.models.functions import Coalesce, Greatest

from rest_framework import filters


class TrigramProductSearchFilter(filters.SearchFilter):
    """
    SearchFilter finds CANDIDATES; this filter RANKS them.

    Stage 1 (inherited SearchFilter): icontains over the view's
    search_fields narrows the queryset (backed by the functional
    Upper(col) GIN trigram indexes).

    Stage 2 (here): a weighted trigram relevance score is annotated
    per term and the queryset is ordered by it. Weights encode a
    business decision - which field a customer "means" when
    searching - e.g. an SKU hit is a stronger signal than a
    description mention.

    Variants use Max() over the join: a product with 4 variants is
    ranked by its BEST variant match, not dragged down by weak ones.
    """

    similarity_weights = {
        "name": 1.00,
        "slug": 0.85,
        "brand": 0.90,
        "variant_sku": 0.95,
        "variant_name": 0.85,
        "description": 0.40,
    }

    def get_relevance_ordering(self, search_terms):
        """
        Ordering used by the view/pagination when search is active.

        Ties are broken by -created_at and id so the cursor stays
        deterministic.
        """

        return (
            "-search_relevance",
            "-created_at",
            "id",
        )

    def build_relevance_annotation(self, term):
        weights = self.similarity_weights

        name_similarity = (
            TrigramSimilarity("name", term)
            * weights["name"]
        )

        slug_similarity = (
            TrigramSimilarity("slug", term)
            * weights["slug"]
        )

        brand_similarity = (
            TrigramSimilarity("brand__name", term)
            * weights["brand"]
        )

        variant_sku_similarity = (
            Max(
                TrigramSimilarity(
                    "variants__sku",
                    term,
                )
            )
            * weights["variant_sku"]
        )

        variant_name_similarity = (
            Max(
                TrigramSimilarity(
                    "variants__name",
                    term,
                )
            )
            * weights["variant_name"]
        )

        description_similarity = (
            TrigramSimilarity("description", term)
            * weights["description"]
        )

        def zero(expression):
            return Coalesce(
                expression,
                Value(0.0),
                output_field=FloatField(),
            )

        return Greatest(
            zero(name_similarity),
            zero(slug_similarity),
            zero(brand_similarity),
            zero(variant_sku_similarity),
            zero(variant_name_similarity),
            zero(description_similarity),
        )

    def filter_queryset(
        self,
        request,
        queryset,
        view,
    ):
        queryset = super().filter_queryset(
            request,
            queryset,
            view,
        )

        search_terms = self.get_search_terms(request)

        if not search_terms:
            return queryset

        for term in search_terms:
            queryset = queryset.annotate(
                **{
                    f"search_term_{self._term_key(term)}":
                        self.build_relevance_annotation(term),
                },
            )

        relevance_expression = None

        for term in search_terms:
            expression = queryset.query.annotations[
                f"search_term_{self._term_key(term)}"
            ]

            if relevance_expression is None:
                relevance_expression = expression
            else:
                relevance_expression = (
                    relevance_expression + expression
                )

        queryset = queryset.annotate(
            search_relevance=relevance_expression,
        )

        # NOTE: the actual ORDER BY is NOT applied here.
        # CursorPagination always enforces its own ordering and
        # would silently discard an order_by applied in a filter
        # backend; the ranking ordering is exposed via
        # get_relevance_ordering() for the pagination class to
        # pick up (see SearchAwareCursorPagination).
        return queryset

    def _term_key(self, term):
        import hashlib

        return hashlib.sha256(
            term.encode("utf-8")
        ).hexdigest()[:12]
