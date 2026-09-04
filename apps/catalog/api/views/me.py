from rest_framework.response import Response
from rest_framework.views import APIView


class MeView(APIView):

    def get(self, request):
        return Response(
            {
                "id": str(request.user.id),
                "email": request.user.email,
            }
        )