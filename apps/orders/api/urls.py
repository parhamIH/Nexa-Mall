from django.urls import path

from apps.orders.api.views import (
    ShopOrderViewSet,
    UserOrderViewSet,
)


urlpatterns = [
    path(
        "",
        UserOrderViewSet.as_view({
            "get": "list",
        }),
        name="order-list",
    ),

    path(
        "<uuid:pk>/",
        UserOrderViewSet.as_view({
            "get": "retrieve",
        }),
        name="order-detail",
    ),

    path(
        "manage/shops/<uuid:shop_id>/",
        ShopOrderViewSet.as_view({
            "get": "list",
        }),
        name="shop-order-list",
    ),

    path(
        "manage/shops/<uuid:shop_id>/<uuid:pk>/",
        ShopOrderViewSet.as_view({
            "get": "retrieve",
        }),
        name="shop-order-detail",
    ),
]