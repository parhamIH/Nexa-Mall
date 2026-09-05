from rest_framework.throttling import (
    AnonRateThrottle,
    UserRateThrottle,
)


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class PaymentRateThrottle(UserRateThrottle):
    scope = "payment"


class WebhookRateThrottle(AnonRateThrottle):
    scope = "webhook"