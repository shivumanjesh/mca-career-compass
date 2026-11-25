"""Consistent structured JSON exception handling for DRF."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Normalize DRF error responses to {code, message, details}."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "default_code", "error")
    if hasattr(exc, "get_codes"):
        raw_codes = exc.get_codes()
        if isinstance(raw_codes, str):
            code = raw_codes

    message = "Request failed."
    details = response.data

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        message = "Validation failed. Please review the highlighted fields."
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        message = "Authentication is required to access this resource."
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        message = "You do not have permission to perform this action."
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        message = "The requested resource was not found."
    elif isinstance(details, dict) and isinstance(details.get("detail"), str):
        message = details["detail"]

    if isinstance(details, dict) and isinstance(details.get("detail"), str):
        message = details["detail"]

    response.data = {
        "code": str(code),
        "message": message,
        "details": details,
    }
    return response

