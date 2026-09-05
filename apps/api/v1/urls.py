from django.urls import include, path

from apps.api.auth_views import (
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)


urlpatterns = [
    path(
        "auth/token/",
        ThrottledTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "auth/token/refresh/",
        ThrottledTokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "catalog/",
        include("apps.catalog.api.urls"),
    ),

    path(
        "cart/",
        include("apps.cart.api.urls"),
    ),

    path(
        "checkout/",
        include("apps.checkout.api.urls"),
    ),

    path(
        "orders/",
        include("apps.orders.api.urls"),
    ),

    path(
        "payments/",
        include("apps.payments.api.urls"),
    ),
]