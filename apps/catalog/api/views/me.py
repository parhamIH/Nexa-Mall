from drf_spectacular.utils import (
    OpenApiTypes,
    extend_schema,
)
from rest_framework.views import APIView

from apps.api.responses import success_response


class MeView(APIView):

    @extend_schema(
        responses={
            200: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request):
        return success_response(
            data={
                "id": str(request.user.id),
                "email": request.user.email,
                "version": request.version,
            },
        )