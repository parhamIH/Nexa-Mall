from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, permissions, viewsets

from apps.api.pagination import StandardPagination
from apps.api.responses import success_response
from apps.catalog.api.filters import ProductFilter
from apps.catalog.api.serializers import (
    ProductDetailResponseSerializer,
    ProductListResponseSerializer,
    ProductListSerializer,
    ProductManagementSerializer,
)
from apps.catalog.cache import (
    get_product_detail,
    set_product_detail,
)
from apps.catalog.selectors.product import ProductSelector
from apps.catalog.services.product import ProductService
from apps.tenants.api.permissions import CanManageShopCatalog


class ProductPublicViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProductListSerializer

    permission_classes = [
        permissions.AllowAny,
    ]

    pagination_class = StandardPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "slug",
        "description",
        "brand__name",
        "variants__sku",
        "variants__name",
    ]

    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
        "slug",
    ]

    ordering = [
        "-created_at",
        "id",
    ]

    def get_queryset(self):
        return ProductSelector.public_products()

    @extend_schema(
        responses=ProductListResponseSerializer,
    )
    def list(
        self,
        request,
        *args,
        **kwargs,
    ):
        return super().list(
            request,
            *args,
            **kwargs,
        )

    @extend_schema(
        responses=ProductDetailResponseSerializer,
    )
    def retrieve(
        self,
        request,
        *args,
        **kwargs,
    ):
        product_id = kwargs["pk"]

        cached_data = get_product_detail(
            product_id=product_id,
            version=request.version or "v1",
        )

        if cached_data is not None:
            return success_response(
                data=cached_data,
            )

        product = self.get_object()

        data = self.get_serializer(
            product,
        ).data

        set_product_detail(
            product_id=product.id,
            data=data,
            version=request.version or "v1",
        )

        return success_response(
            data=data,
        )


class ProductManagementViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProductManagementSerializer

    permission_classes = [
        CanManageShopCatalog,
    ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "slug",
        "description",
        "brand__name",
        "variants__sku",
        "variants__name",
    ]

    ordering_fields = [
        "name",
        "status",
        "created_at",
        "updated_at",
        "slug",
    ]

    ordering = [
        "-created_at",
        "id",
    ]

    def get_queryset(self):
        return ProductSelector.management_products(
            user=self.request.user,
            shop_id=self.kwargs["shop_id"],
        )

    def perform_create(self, serializer):
        ProductService.create_product(
            shop_id=self.kwargs["shop_id"],
            validated_data=serializer.validated_data,
            user=self.request.user,
        )

    def perform_update(self, serializer):
        ProductService.update_product(
            product=self.get_object(),
            validated_data=serializer.validated_data,
            user=self.request.user,
        )

    def perform_destroy(self, instance):
        ProductService.delete_product(
            product=instance,
            user=self.request.user,
        )