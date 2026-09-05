from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.orders.api.serializers import OrderSerializer
from apps.orders.selectors.order import OrderSelector
from apps.tenants.api.permissions import CanManageShopOrders


class UserOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        return OrderSelector.user_orders(
            user=self.request.user,
        )


class ShopOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderSerializer

    permission_classes = [
        IsAuthenticated,
        CanManageShopOrders,
    ]

    def get_queryset(self):
        return OrderSelector.shop_orders(
            user=self.request.user,
            shop_id=self.kwargs["shop_id"],
        )