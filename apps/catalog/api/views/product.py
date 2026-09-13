from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, permissions, viewsets
from rest_framework.exceptions import NotFound

from apps.api.cache import AtomicCacheAside
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
    PRODUCT_DETAIL_LOCK_TIMEOUT,
    PRODUCT_NOT_FOUND,
    get_product_detail,
    product_detail_cache_timeout,
    product_detail_key,
    product_detail_lock_key,
    set_product_detail,
    set_product_not_found,
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

        version = request.version or "v1"

        # Fast path before taking any lock: a cached representation
        # is served as-is; a cached NOT_FOUND marker is a negative
        # cache hit and short-circuits to 404 without touching the
        # database (cache penetration protection).
        cached_data = get_product_detail(
            product_id=product_id,
            version=version,
        )

        if cached_data == PRODUCT_NOT_FOUND:
            raise NotFound(
                "Product not found.",
            )

        if cached_data is not None:
            return success_response(
                data=cached_data,
            )

        cache_aside = AtomicCacheAside(
            key=product_detail_key(
                product_id=product_id,
                version=version,
            ),
            lock_key=product_detail_lock_key(
                product_id=product_id,
                version=version,
            ),
            timeout=product_detail_cache_timeout,
            lock_timeout=PRODUCT_DETAIL_LOCK_TIMEOUT,
            # The loader publishes both outcomes itself with the
            # correct jittered domain TTL (positive 300±60s,
            # negative 60±10s); the helper only coordinates, it must
            # not re-publish with its own single timeout.
            set_loader_value=False,
        )

        def load_product():
            product = (
                ProductSelector.public_products()
                .filter(
                    id=product_id,
                )
                .first()
            )

            if product is None:
                # Publish the absence with the short negative TTL
                # so repeated attacks on the same unknown id stop
                # reaching the database.
                set_product_not_found(
                    product_id=product_id,
                    version=version,
                )

                return PRODUCT_NOT_FOUND

            data = self.get_serializer(
                product,
            ).data

            set_product_detail(
                product_id=product.id,
                data=data,
                version=version,
            )

            return data

        data = cache_aside.get(
            loader=load_product,
        )

        if data == PRODUCT_NOT_FOUND:
            raise NotFound(
                "Product not found.",
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