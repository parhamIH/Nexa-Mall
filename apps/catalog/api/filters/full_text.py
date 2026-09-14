from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)
from django.db.models import (
    Exists,
    IntegerField,
    OuterRef,
    Q,
)
from django.db.models.functions import Cast
from rest_framework import filters
from rest_framework.settings import api_settings

from apps.catalog.models import ProductVariant


# ts_rank() returns `real` (float4, ~7 significant digits). DRF cursor
# pagination encodes the boundary position as str(rank) and later
# filters `rank < position`: the true float4 (e.g. 0.67547458410263)
# lies BELOW its shortest round-trip decimal (0.6754746), so the
# boundary row itself still passes the filter and the next page
# repeats it. Scaling to an integer makes cursor positions exact,
# comparable and deterministic (sub-1e-5 rank differences collapse
# into ties broken by -created_at, id).
RANK_SCALE = 100000


class ProductFullTextSearchFilter(
    filters.BaseFilterBackend,
):
    """
    Token-based full-text search over the product document
    (name A / slug B / description D), with the existing
    brand/variant candidate paths kept as fallbacks.

    Stages:
    - SearchVector + SearchQuery + SearchRank: tsvector matching
      against the GIN expression index, scored by weighted rank
      (a name hit outweighs a description mention)
    - Candidates = FTS match OR brand icontains OR a variant
      sku/name icontains (via Exists - no join duplication), so
      the previous API contract (find via brand/SKU) is preserved
    - Products matched ONLY through the fallback paths rank 0 and
      sort last; unifying trigram similarity with FTS rank is the
      hybrid-search step, not this one

    search_type="websearch": user-style input ("red running shoes",
    quotes, minus) never raises; config="simple" matches the index.
    """

    search_param = api_settings.SEARCH_PARAM

    fts_vector = (
        SearchVector(
            "name",
            weight="A",
            config="simple",
        )
        + SearchVector(
            "slug",
            weight="B",
            config="simple",
        )
        + SearchVector(
            "description",
            weight="D",
            config="simple",
        )
    )

    def filter_queryset(
        self,
        request,
        queryset,
        view,
    ):
        search = request.query_params.get(
            self.search_param,
        )

        if not search:
            return queryset

        query = SearchQuery(
            search,
            search_type="websearch",
            config="simple",
        )

        vector = self.fts_vector

        variant_matches = (
            ProductVariant.objects
            .filter(
                product_id=OuterRef("pk"),
            )
            .filter(
                Q(
                    sku__icontains=search,
                )
                | Q(
                    name__icontains=search,
                )
            )
        )

        queryset = queryset.annotate(
            search_vector=vector,
            search_rank=Cast(
                SearchRank(
                    vector,
                    query,
                )
                * RANK_SCALE,
                IntegerField(),
            ),
        )

        queryset = queryset.filter(
            Q(
                search_vector=query,
            )
            | Q(
                brand__name__icontains=search,
            )
            | Exists(
                variant_matches,
            )
        )

        # The ORDER BY is also picked up by the search-aware cursor
        # pagination (which enforces its own ordering and would
        # otherwise discard an order_by applied here).
        return (
            queryset
            .order_by(
                "-search_rank",
                "-created_at",
                "id",
            )
            .distinct()
        )
