from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.catalog.api.views import (
    MeView,
    ProductManagementViewSet,
    ProductPublicViewSet,
)


public_router = DefaultRouter()

public_router.register(
    "products",
    ProductPublicViewSet,
    basename="product",
)


management_router = DefaultRouter()

management_router.register(
    "products",
    ProductManagementViewSet,
    basename="management-product",
)


urlpatterns = [
    path(
        "me/",
        MeView.as_view(),
        name="me",
    ),

    path(
        "",
        include(public_router.urls),
    ),

    path(
        "manage/shops/<uuid:shop_id>/",
        include(management_router.urls),
    ),
]