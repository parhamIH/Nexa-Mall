from rest_framework import mixins, permissions, viewsets

from apps.catalog.api.serializers import ProductListSerializer
from apps.catalog.selectors.product import ProductSelector


class ProductViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProductListSerializer
    permission_classes = [
        permissions.AllowAny,
    ]

    def get_queryset(self):
        return ProductSelector.public_products()