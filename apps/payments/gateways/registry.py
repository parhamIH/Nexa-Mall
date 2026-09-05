from django.core.exceptions import ValidationError

from apps.payments.gateways import MockPaymentGateway


_GATEWAYS = {
    MockPaymentGateway.name: MockPaymentGateway,
}


def get_payment_gateway(
    *,
    provider,
):
    gateway_class = _GATEWAYS.get(provider)

    if gateway_class is None:
        raise ValidationError(
            f"Unsupported payment provider: {provider}"
        )

    return gateway_class()