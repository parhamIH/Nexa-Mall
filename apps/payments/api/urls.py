from django.urls import path

from apps.payments.api.views import (
    PaymentAttemptCreateView,
    PaymentCreateView,
    PaymentDetailView,
    PaymentWebhookView,
)


urlpatterns = [
    path(
        "",
        PaymentCreateView.as_view(),
        name="payment-create",
    ),

    path(
        "webhooks/<str:provider>/",
        PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),

    path(
        "<uuid:payment_id>/",
        PaymentDetailView.as_view(),
        name="payment-detail",
    ),

    path(
        "<uuid:payment_id>/attempts/",
        PaymentAttemptCreateView.as_view(),
        name="payment-attempt-create",
    ),
]