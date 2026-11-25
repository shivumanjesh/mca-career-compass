"""Standard pagination classes."""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Paginate list responses consistently across all modules."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

