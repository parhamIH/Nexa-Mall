import random

from django.core.cache import cache


PRODUCT_DETAIL_CACHE_VERSION = "v1"

PRODUCT_DETAIL_CACHE_TIMEOUT = 300

# Avalanche protection: each fill gets a TTL spread over
# [300 - 60, 300 + 60] seconds, so products cached together do
# not all expire at the same instant and hammer the database.
PRODUCT_DETAIL_CACHE_JITTER = 60

PRODUCT_DETAIL_LOCK_TIMEOUT = 10

PRODUCT_NOT_FOUND = "__NEXA_PRODUCT_NOT_FOUND__"

# Negative entries get a much shorter TTL than positive data: if an
# admin creates the product later, the window where the API wrongly
# serves 404 stays small (cache staleness bound for misses).
PRODUCT_NOT_FOUND_TIMEOUT = 60

PRODUCT_NOT_FOUND_JITTER = 10


def product_detail_key(
    *,
    product_id,
    version=PRODUCT_DETAIL_CACHE_VERSION,
):
    return (
        f"nexa:{version}:catalog:"
        f"product:detail:{product_id}"
    )


def product_detail_lock_key(
    *,
    product_id,
    version=PRODUCT_DETAIL_CACHE_VERSION,
):
    return (
        f"nexa:{version}:lock:"
        f"catalog:product:detail:{product_id}"
    )


def product_detail_cache_timeout():
    return random.randint(
        PRODUCT_DETAIL_CACHE_TIMEOUT
        - PRODUCT_DETAIL_CACHE_JITTER,
        PRODUCT_DETAIL_CACHE_TIMEOUT
        + PRODUCT_DETAIL_CACHE_JITTER,
    )


def product_not_found_cache_timeout():
    return random.randint(
        PRODUCT_NOT_FOUND_TIMEOUT
        - PRODUCT_NOT_FOUND_JITTER,
        PRODUCT_NOT_FOUND_TIMEOUT
        + PRODUCT_NOT_FOUND_JITTER,
    )


def get_product_detail(
    *,
    product_id,
    version=PRODUCT_DETAIL_CACHE_VERSION,
):
    return cache.get(
        product_detail_key(
            product_id=product_id,
            version=version,
        )
    )


def set_product_detail(
    *,
    product_id,
    data,
    version=PRODUCT_DETAIL_CACHE_VERSION,
    timeout=None,
):
    if timeout is None:
        # A fresh, jittered TTL per fill (never re-rolled on a
        # cache hit) spreads expirations over time.
        timeout = product_detail_cache_timeout()

    return cache.set(
        product_detail_key(
            product_id=product_id,
            version=version,
        ),
        data,
        timeout=timeout,
    )


def set_product_not_found(
    *,
    product_id,
    version=PRODUCT_DETAIL_CACHE_VERSION,
):
    return cache.set(
        product_detail_key(
            product_id=product_id,
            version=version,
        ),
        PRODUCT_NOT_FOUND,
        timeout=product_not_found_cache_timeout(),
    )


def delete_product_detail(
    *,
    product_id,
    version=PRODUCT_DETAIL_CACHE_VERSION,
):
    return cache.delete(
        product_detail_key(
            product_id=product_id,
            version=version,
        )
    )
