from dataclasses import dataclass

from apps.catalog.models.product import Product
from apps.catalog.search.ranking import (
    DEFAULT_RANKING_WEIGHTS,
    RankingWeights,
)


class InvalidSearchScope(ValueError):
    """Raised when tenant/shop scope is inconsistent."""


@dataclass(frozen=True)
class SearchScope:
    tenant_id: object
    shop_id: object


class CatalogSearchFactory:
    """
    Builds a tenant/shop-scoped product queryset and exposes
    the configured ranking weights for search execution.
    """

    def __init__(
        self,
        *,
        scope: SearchScope,
        weights: RankingWeights = DEFAULT_RANKING_WEIGHTS,
    ) -> None:
        self.scope = scope
        self.weights = weights

    @classmethod
    def from_tenant_and_shop(
        cls,
        *,
        tenant,
        shop,
        weights: RankingWeights = DEFAULT_RANKING_WEIGHTS,
    ) -> "CatalogSearchFactory":
        if shop.tenant_id != tenant.pk:
            raise InvalidSearchScope(
                "The selected shop does not belong to the selected tenant."
            )

        return cls(
            scope=SearchScope(
                tenant_id=tenant.pk,
                shop_id=shop.pk,
            ),
            weights=weights,
        )

    def queryset(self):
        """
        Candidate source for search.

        Tenant scope and shop scope are applied BEFORE search ranking.
        """
        return (
            Product.objects
            .filter(
                shop_id=self.scope.shop_id,
                shop__tenant_id=self.scope.tenant_id,
                status=Product.Status.ACTIVE,
            )
            .select_related(
                "shop",
                "brand",
            )
        )