from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db.models import (
    Case,
    FloatField,
    IntegerField,
    Max,
    Q,
    Value,
    When,
)
from django.db.models.functions import (
    Cast,
    Coalesce,
    Upper,
)
from rest_framework import filters
from rest_framework.settings import api_settings


# search_score positions are consumed by cursor pagination: like
# ts_rank, trigram similarity is a float4, so the score is scaled to
# an INTEGER (see ADR-003: the boundary row must not survive its own
# round-tripped position and repeat on the next page). Sub-1e-5
# score differences are ranking noise and collapse into ties broken
# by -created_at, id.
SCORE_SCALE = 100000


class HybridProductSearchFilter(
    filters.BaseFilterBackend,
):
    """Weighted-sum hybrid search: candidates from any signal, ranked
    by a combined score. Candidates come from token (FTS) matches,
    substring (icontains) matches OR name-trigram similarity, so a
    typo'd query ("nike air mx") still retrieves something to rank -
    trigram similarity is not left ranking-only, where a query no
    token/substring path matches would retrieve NOTHING.

    Unifies the two engines built in the previous chapters:
    - FTS (tsvector GIN + SearchRank): "which documents contain
      these tokens" (name A > slug B > description D)
    - trigram (pg_trgm): "how similar is this text" (typo/partial)

    Scoring model (initial weights, to be tuned with real search
    quality data - a business rule, not a technical constant):
        exact name match      + 10.0
        name trigram          4.0 x similarity
        best variant SKU       8.0 x similarity
        brand trigram          5.0 x similarity
        FTS rank               3.0 x rank
        description trigram   1.0 x similarity

    A Weighted Sum (not Greatest): each signal contributes its own
    share to the final score, so a product strong in two channels
    outranks one strong in a single channel. Max() over variants so a
    product with many weak variants cannot farm an artificial boost.
    """

    search_param = api_settings.SEARCH_PARAM

    NAME_EXACT_WEIGHT = 10.0
    NAME_TRIGRAM_WEIGHT = 4.0
    SKU_WEIGHT = 8.0
    BRAND_WEIGHT = 5.0
    FTS_WEIGHT = 3.0
    DESCRIPTION_WEIGHT = 1.0

    # Candidate-generation threshold for the name trigram channel.
    # Measured on the dev catalog: the typo target ("nike air mx" vs
    # "Nike Air Max") scores 0.667 while the nearest unrelated
    # product sits at 0.286. The candidate branch uses the indexable
    # `%` operator (trigram_similar), whose cut-off is pg_trgm's
    # pg_trgm.similarity_threshold GUC (default 0.3, exactly between
    # the measured target and noise). Tune with real query logs, not
    # guesses.

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

        search = search.strip()

        if not search:
            return queryset

        search_query = SearchQuery(
            search,
            search_type="websearch",
            config="simple",
        )

        search_vector = self.fts_vector

        name_similarity = Coalesce(
            TrigramSimilarity(
                "name",
                search,
            ),
            Value(0.0),
            output_field=FloatField(),
        )

        description_similarity = Coalesce(
            TrigramSimilarity(
                "description",
                search,
            ),
            Value(0.0),
            output_field=FloatField(),
        )

        brand_similarity = Coalesce(
            TrigramSimilarity(
                "brand__name",
                search,
            ),
            Value(0.0),
            output_field=FloatField(),
        )

        variant_sku_similarity = Coalesce(
            Max(
                TrigramSimilarity(
                    "variants__sku",
                    search,
                )
            ),
            Value(0.0),
            output_field=FloatField(),
        )

        fts_rank = Coalesce(
            SearchRank(
                search_vector,
                search_query,
            ),
            Value(0.0),
            output_field=FloatField(),
        )

        exact_name_boost = Case(
            When(
                name__iexact=search,
                then=Value(
                    self.NAME_EXACT_WEIGHT,
                ),
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )

        final_score = (
            exact_name_boost
            + name_similarity
            * Value(
                self.NAME_TRIGRAM_WEIGHT,
            )
            + variant_sku_similarity
            * Value(
                self.SKU_WEIGHT,
            )
            + brand_similarity
            * Value(
                self.BRAND_WEIGHT,
            )
            + fts_rank
            * Value(
                self.FTS_WEIGHT,
            )
            + description_similarity
            * Value(
                self.DESCRIPTION_WEIGHT,
            )
        )

        variant_match = Q(
            variants__sku__icontains=search,
        ) | Q(
            variants__name__icontains=search,
        )

        queryset = queryset.annotate(
            # The vector is annotated so the candidate filter below can
            # match on it (and so the predicate expression is identical
            # to the product_fts_search_idx GIN index expression).
            search_vector=search_vector,
            # Typo-tolerance candidate channel. The `%` operator must
            # be applied to the SAME expression the functional GIN
            # index is built on (upper(name) gin_trgm_ops): verified
            # Bitmap Index Scan on product_name_trgm_idx. A per-row
            # `similarity >= t` predicate is NOT indexable and, inside
            # this OR, would drag the whole filter back to a seq scan
            # over the catalog - losing the GIN paths of every OTHER
            # branch too. similarity() lowercases its trigrams, so
            # UPPER(name) % raw query matches case-insensitively.
            search_name_upper=Upper("name"),
            search_score=Cast(
                final_score * SCORE_SCALE,
                IntegerField(),
            ),
        )

        queryset = queryset.filter(
            Q(
                search_vector=search_query,
            )
            | Q(
                name__icontains=search,
            )
            | Q(
                slug__icontains=search,
            )
            | Q(
                description__icontains=search,
            )
            | Q(
                brand__name__icontains=search,
            )
            # Typo-tolerant retrieval: a name trigram-similar to the
            # (possibly mistyped) query becomes a candidate even when
            # no token or substring path matches it. Cut-off = the
            # pg_trgm.similarity_threshold GUC (0.3 by default).
            | Q(
                search_name_upper__trigram_similar=(
                    search
                ),
            )
            | variant_match,
        )

        # Ordering is also adopted by the search-aware cursor
        # pagination (which enforces its own ordering and would
        # otherwise discard an order_by applied here).
        return (
            queryset
            .order_by(
                "-search_score",
                "-created_at",
                "id",
            )
            .distinct()
        )