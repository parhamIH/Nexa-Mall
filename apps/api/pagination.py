from rest_framework.pagination import (
    CursorPagination,
    PageNumberPagination,
)
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "data": data,
                "meta": {
                    "count": self.page.paginator.count,
                    "page": self.page.number,
                    "pages": self.page.paginator.num_pages,
                    "page_size": self.get_page_size(
                        self.request
                    ),
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
            }
        )


class StandardCursorPagination(CursorPagination):
    """
    Cursor pagination for large, read-heavy timelines (public catalog).

    Instead of page/offset (which must walk past every skipped row on
    deep pages), clients follow the opaque `cursor` link: traversal is
    stable as new records are inserted, at the cost of not being able
    to jump to an arbitrary page number.

    Cursor ordering must be stable, immutable and (ideally) unique:
    -created_at is immutable after creation and backed by the
    (status, created_at) index for the public listing query.

    No arbitrary ?ordering= on cursor endpoints: each ordering would
    need its own index, cursor semantics and stability analysis.
    Filters and search stay; ordering is fixed by the cursor.
    """

    page_size = 20

    page_size_query_param = "page_size"

    max_page_size = 100

    cursor_query_param = "cursor"

    ordering = "-created_at"

    template = None

    def get_paginated_response(self, data):
        # No count/pages on purpose: COUNT(*) over a huge dataset is
        # an extra full scan, and "page 37 of 1842" is not what a
        # cursor API is for - next/previous is the contract.
        return Response(
            {
                "data": data,
                "meta": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "page_size": self.get_page_size(
                        self.request,
                    ),
                },
            }
        )