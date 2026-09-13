import random
from hashlib import sha256
from urllib.parse import urlencode

from django.core.cache import cache


PRODUCT_LIST_CACHE_TIMEOUT = 120

PRODUCT_LIST_CACHE_JITTER = 30

PRODUCT_LIST_LOCK_TIMEOUT = 10

# The list namespace version lives in a single, non-expiring key.
# Bumping it invalidates EVERY list combination at once without
# scanning or deleting thousands of hash keys (lazy invalidation:
# old entries simply become unreachable and expire via their TTL).
PRODUCT_LIST_NAMESPACE_KEY = (
    "nexa:catalog:product:list:namespace"
)

# Only parameters that actually affect the public product list
# representation participate in the cache key; anything else a
# client appends must not mint a new cache entry (key explosion
# protection).
PRODUCT_LIST_RELEVANT_PARAMETERS = (
    "status",
    "brand",
    "category",
    "shop",
    "search",
    "ordering",
    "page",
    "page_size",
)


def _ensure_product_list_namespace():
    """
    Make sure the namespace version exists.

    The key intentionally has no expiration.
    """
    version = cache.get(
        PRODUCT_LIST_NAMESPACE_KEY,
    )

    if version is not None:
        return int(version)

    created = cache.add(
        PRODUCT_LIST_NAMESPACE_KEY,
        1,
        timeout=None,
    )

    if created:
        return 1

    return int(
        cache.get(
            PRODUCT_LIST_NAMESPACE_KEY,
        )
    )


def product_list_namespace_version():
    return _ensure_product_list_namespace()


def bump_product_list_namespace():
    """
    Bump the namespace version.

    Existing list cache entries remain physically present
    until their TTL expires, but all new requests use the
    new namespace and therefore cannot read old entries.
    """
    _ensure_product_list_namespace()

    return int(
        cache.incr(
            PRODUCT_LIST_NAMESPACE_KEY,
        )
    )


def product_list_cache_timeout():
    # Shorter than the detail cache (120±30 vs 300±60): a
    # collection is affected by more mutation types (new product,
    # renames, variant/brand/category changes) and has many more
    # query combinations.
    return random.randint(
        PRODUCT_LIST_CACHE_TIMEOUT
        - PRODUCT_LIST_CACHE_JITTER,
        PRODUCT_LIST_CACHE_TIMEOUT
        + PRODUCT_LIST_CACHE_JITTER,
    )


def _canonical_product_list_query(
    *,
    query_params,
):
    """
    Canonicalize only the relevant query parameters.

    Sorted by parameter name, then by value order, so two
    requests differing only in raw parameter order produce the
    SAME cache key. Unknown parameters are ignored entirely.
    """

    pairs = []

    for name in sorted(
        PRODUCT_LIST_RELEVANT_PARAMETERS,
    ):
        values = query_params.getlist(name)

        for value in values:
            pairs.append(
                (
                    name,
                    value,
                )
            )

    return urlencode(
        pairs,
        doseq=True,
    )


def _product_list_digest(
    *,
    query_params,
):
    canonical_query = _canonical_product_list_query(
        query_params=query_params,
    )

    return sha256(
        canonical_query.encode("utf-8")
    ).hexdigest()


def product_list_key(
    *,
    query_params,
    version="v1",
):
    namespace = product_list_namespace_version()

    return (
        f"nexa:{version}:catalog:"
        f"product:list:"
        f"v{namespace}:"
        f"{_product_list_digest(query_params=query_params)}"
    )


def product_list_lock_key(
    *,
    query_params,
    version="v1",
):
    namespace = product_list_namespace_version()

    return (
        f"nexa:{version}:lock:"
        f"catalog:product:list:"
        f"v{namespace}:"
        f"{_product_list_digest(query_params=query_params)}"
    )
