from django.urls import path

from apps.cart.api.views import (
    CartItemCreateView,
    CartItemDetailView,
    CartView,
)


urlpatterns = [
    path(
        "shops/<uuid:shop_id>/",
        CartView.as_view(),
        name="cart-detail",
    ),

    path(
        "shops/<uuid:shop_id>/items/",
        CartItemCreateView.as_view(),
        name="cart-item-create",
    ),

    path(
        "items/<uuid:item_id>/",
        CartItemDetailView.as_view(),
        name="cart-item-detail",
    ),
]