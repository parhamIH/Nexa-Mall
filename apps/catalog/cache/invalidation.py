from collections.abc import Iterable

from django.db import transaction

from apps.catalog.cache.list import (
    bump_product_list_namespace,
)
from apps.catalog.cache.product import (
    delete_product_detail,
)


def invalidate_product(
    *,
    product_id,
):
    """
    Invalidate every cache representation derived from a single
    product, AFTER the surrounding database transaction commits.

    Two representations depend on one product:
    - the detail entry: deleted explicitly (object invalidation)
    - every list entry containing it: invalidated by bumping the
      list namespace version once (collection invalidation - old
      keys become unreachable and expire via their TTL)

    Why on_commit: deleting the cache inside the transaction means a
    later ROLLBACK leaves the database unchanged while the cache is
    already gone - the system still works (next request is a miss
    and reloads), but the delete was pointless and the entry's TTL
    clock restarts for nothing. Registering on COMMIT keeps
    DB-update-then-cache-delete truly ordered.
    """

    def _invalidate():
        delete_product_detail(
            product_id=product_id,
        )

        bump_product_list_namespace()

    transaction.on_commit(
        _invalidate,
    )


def invalidate_products(
    *,
    product_ids: Iterable,
):
    """
    Invalidate cache representations for several products at once
    (e.g. a brand/category change affecting many products).

    The ids are materialized into a tuple BEFORE the callback is
    registered: generators evaluated lazily after commit could miss
    rows mutated inside this transaction, and the callback must not
    depend on query state that may have changed by the time it runs.

    The list namespace is bumped ONCE for the whole mutation set:
    a brand update touching 100 products means 100 detail deletes +
    a single namespace bump, not 100 bumps.
    """

    product_ids = tuple(
        product_ids,
    )

    if not product_ids:
        return

    def _invalidate():
        for product_id in product_ids:
            delete_product_detail(
                product_id=product_id,
            )

        bump_product_list_namespace()

    transaction.on_commit(
        _invalidate,
    )


def invalidate_brand_products(
    *,
    brand_id,
):
    """
    Fan-out invalidation: a brand attribute (e.g. name) lives inside
    the product detail representation (brand_name field), so a
    brand change makes every product of that brand stale.

    The affected ids are collected at CALL time - i.e. BEFORE the
    surrounding transaction mutates anything - and materialized by
    invalidate_products, so the invalidation set is exactly the set
    of products that referenced the brand at mutation time.
    """

    from apps.catalog.models import Product

    product_ids = Product.objects.filter(
        brand_id=brand_id,
    ).values_list(
        "id",
        flat=True,
    )

    invalidate_products(
        product_ids=product_ids,
    )
