from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class BusinessRuleViolation(APIException):
    status_code = 400

    default_detail = "Business rule violation."
    default_code = "business_rule_violation"


def custom_exception_handler(exc, context):
    response = exception_handler(
        exc,
        context,
    )

    if response is None:
        return response

    status_code = response.status_code

    error_code = getattr(
        exc,
        "default_code",
        "api_error",
    )

    if status_code == 400:
        # DRF's ValidationError ships with default_code "invalid";
        # map it to our API contract's "validation_error" while
        # keeping custom codes (e.g. BusinessRuleViolation) intact.
        if error_code == "invalid":
            error_code = "validation_error"

        message = "Validation failed."

    elif status_code == 401:
        error_code = "authentication_required"
        message = "Authentication is required."

    elif status_code == 403:
        error_code = "permission_denied"
        message = "You do not have permission to perform this action."

    elif status_code == 404:
        error_code = "not_found"
        message = "The requested resource was not found."

    elif status_code == 405:
        error_code = "method_not_allowed"
        message = "This HTTP method is not allowed."

    elif status_code == 429:
        error_code = "rate_limited"
        message = "Too many requests."

    else:
        message = "An API error occurred."

    response.data = {
        "error": {
            "code": error_code,
            "message": message,
            "details": response.data,
        }
    }

    return response