from rest_framework.response import Response


def success_response(
    *,
    data=None,
    meta=None,
    status_code=200,
    headers=None,
):
    return Response(
        {
            "data": data,
            "meta": meta or {},
        },
        status=status_code,
        headers=headers,
    )