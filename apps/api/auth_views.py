from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.api.throttling import AuthRateThrottle


class ThrottledTokenObtainPairView(
    TokenObtainPairView
):
    throttle_classes = [
        AuthRateThrottle,
    ]


class ThrottledTokenRefreshView(
    TokenRefreshView
):
    throttle_classes = [
        AuthRateThrottle,
    ]