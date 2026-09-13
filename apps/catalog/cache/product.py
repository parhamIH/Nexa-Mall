from django.core.cache import cache


PRODUCT_DETAIL_CACHE_VERSION = "v1"

PRODUCT_DETAIL_CACHE_TIMEOUT = 300


def product_detail_key(
    *,
    product_id,
    version=PRODUCT_DETAIL_CACHE_VERSION,
):
    return (
        f"nexa:{version}:catalog:"
        f"product:detail:{product_id}"
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
    timeout=PRODUCT_DETAIL_CACHE_TIMEOUT,
):
    cache.set(
        product_detail_key(
            product_id=product_id,
            version=version,
        ),
        data,
        timeout=timeout,
    )


def delete_product_detail(
    *,
    product_id,
    version=PRODUCT_DETAIL_CACHE_VERSION,
):
    cache.delete(
        product_detail_key(
            product_id=product_id,
            version=version,
        )
    )
