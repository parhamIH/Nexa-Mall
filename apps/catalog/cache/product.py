import random
import time

from django.core.cache import cache


PRODUCT_DETAIL_CACHE_VERSION = "v1"

# Stale-while-revalidate (hot-key / breakdown protection):
# - fresh: served instantly, no source access
# - stale window (fresh..hard): previous value still served
#   instantly while exactly one worker revalidates
# - hard: the Redis TTL; past it the key is a real miss and plain
#   single-flight waiting applies again
PRODUCT_DETAIL_FRESH_TIMEOUT = 60

PRODUCT_DETAIL_HARD_TIMEOUT = 300

# Avalanche protection: each fill draws a hard TTL spread over
# [hard - jitter, hard + jitter] seconds, so products cached
# together do not all expire at the same instant.
PRODUCT_DETAIL_HARD_TIMEOUT_JITTER = 60

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


def product_detail_hard_cache_timeout():
    return random.randint(
        PRODUCT_DETAIL_HARD_TIMEOUT
        - PRODUCT_DETAIL_HARD_TIMEOUT_JITTER,
        PRODUCT_DETAIL_HARD_TIMEOUT
        + PRODUCT_DETAIL_HARD_TIMEOUT_JITTER,
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
    """Publish the SWR envelope: payload + stale_at (soft window)."""

    if timeout is None:
        # A fresh, jittered hard TTL per fill (never re-rolled on a
        # cache hit) spreads expirations over time.
        timeout = product_detail_hard_cache_timeout()

    envelope = {
        "data": data,
        "stale_at": time.time()
        + PRODUCT_DETAIL_FRESH_TIMEOUT,
    }

    return cache.set(
        product_detail_key(
            product_id=product_id,
            version=version,
        ),
        envelope,
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
