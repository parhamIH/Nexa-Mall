from django.contrib import admin
from django.urls import include, path

from apps.api.auth_views import (
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "api/v1/auth/token/",
        ThrottledTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/v1/auth/token/refresh/",
        ThrottledTokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "api/v1/catalog/",
        include(
            "apps.catalog.api.urls",
        ),
    ),

    path(
        "api/v1/cart/",
        include(
            "apps.cart.api.urls",
        ),
    ),

    path(
        "api/v1/checkout/",
        include(
            "apps.checkout.api.urls",
        ),
    ),

    path(
        "api/v1/orders/",
        include(
            "apps.orders.api.urls",
        ),
    ),

    path(
        "api/v1/payments/",
        include(
            "apps.payments.api.urls",
        ),
    ),
]