from collections.abc import Callable

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.catalog.api.filters.hybrid_search import HybridProductSearchFilter
from apps.catalog.selectors.product import ProductSelector


class HybridSearchAdapter:
    """
    Adapter between the REAL DRF hybrid search filter and the
    benchmark/evaluation layer.

    The benchmark must measure the SAME ranking the public API
    serves - not a parallel implementation - otherwise a green
    benchmark can coexist with a worse API. This adapter therefore
    runs HybridProductSearchFilter itself and only translates the
    result to the benchmark's lingua franca: a plain list of
    product slugs.

    Dependency inversion: the benchmark layer (SearchFunction =
    Callable[[str], list[str]]) knows nothing about DRF, the ORM or
    PostgreSQL; the adapter is the single place where that coupling
    lives, and it can later point the same benchmark at a different
    engine unchanged.

    Multi-tenant note: for production use, pass a SCOPED
    base_queryset (tenant/shop) so that isolation and business
    filters apply BEFORE candidate generation and ranking:

        Tenant scope -> filters -> search -> ranking

    Ranking over the whole catalog and filtering afterwards would
    be both a correctness and a performance bug.
    """

    def __init__(
        self,
        base_queryset: Callable[[], object] | None = None,
    ) -> None:
        # API PARITY by default: the public list endpoint serves
        # ProductSelector.public_products(), so the benchmark measures
        # over the same scope. Product.objects.all would rank DRAFT or
        # ARCHIVED products the API never serves - a benchmark green
        # while the API shows different results is exactly what this
        # chapter exists to prevent.
        self.base_queryset = (
            base_queryset
            or ProductSelector.public_products
        )

    def search(self, query: str, limit: int = 20) -> list[str]:
        factory = APIRequestFactory()

        django_request = factory.get(
            "/api/v1/products/",
            {"search": query},
        )

        request = Request(django_request)

        queryset = self.base_queryset()

        # view=None is sufficient: HybridProductSearchFilter reads
        # only request + queryset, never the view.
        filtered_queryset = HybridProductSearchFilter().filter_queryset(
            request,
            queryset,
            view=None,
        )

        return list(
            filtered_queryset
            .values_list("slug", flat=True)[:limit]
        )
