from drf_spectacular.utils import (
    OpenApiTypes,
    extend_schema,
)
from rest_framework.response import Response
from rest_framework.views import APIView


class MeView(APIView):

    @extend_schema(
        responses={
            200: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request):
        return Response(
            {
                "id": str(request.user.id),
                "email": request.user.email,
            }
        )