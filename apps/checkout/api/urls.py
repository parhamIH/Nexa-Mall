from django.urls import path

from apps.checkout.api.views import CheckoutCreateView


urlpatterns = [
    path(
        "",
        CheckoutCreateView.as_view(),
        name="checkout-create",
    ),
]
