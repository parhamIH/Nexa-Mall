from collections.abc import Iterable

from django.db import transaction

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

    Why on_commit: deleting the cache inside the transaction means a
    later ROLLBACK leaves the database unchanged while the cache is
    already gone - the system still works (next request is a miss
    and reloads), but the delete was pointless and the entry's TTL
    clock restarts for nothing. Registering on COMMIT keeps
    DB-update-then-cache-delete truly ordered: rollback leaves the
    cache untouched, commit invalidates immediately after.
    """

    transaction.on_commit(
        lambda: delete_product_detail(
            product_id=product_id,
        )
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
    """

    product_ids = tuple(product_ids)

    def _invalidate():
        for product_id in product_ids:
            delete_product_detail(
                product_id=product_id,
            )

    transaction.on_commit(
        _invalidate,
    )
