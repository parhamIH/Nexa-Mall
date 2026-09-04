from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.catalog.api.views import ProductViewSet
from apps.catalog.api.views.me import MeView


router = DefaultRouter()

router.register(
    "products",
    ProductViewSet,
    basename="product",
)

urlpatterns = [
    path(
        "me/",
        MeView.as_view(),
        name="me",
    ),
]

urlpatterns += router.urls