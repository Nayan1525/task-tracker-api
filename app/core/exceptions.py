"""Domain exception hierarchy and the centralized exception-to-response map.

Implements `core/error-handling.md`: an `AppError` base for domain
exceptions plus one `to_error_response()` function producing the error
envelope from `core/api-design.md`. The actual handler registration (which
needs the FastAPI app object) lives in main.py.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base for all domain exceptions raised out of the service layer.

    `code` is the stable, machine-readable UPPER_SNAKE_CASE string from
    `core/api-design.md` — set explicitly (not derived from the class name)
    so renaming the class can't silently change the client-facing contract.
    """

    code: str = "APP_ERROR"
    status_code: int = 500
    details: dict | None = None


class NotFoundError(AppError):
    """A requested resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404

    def __init__(self, resource: str, resource_id: object) -> None:
        self.resource = resource
        self.resource_id = resource_id
        self.details = {"resource": resource, "resource_id": resource_id}
        super().__init__(f"{resource} {resource_id} not found")


class InvalidReminderConfigurationError(AppError):
    """A task would end up with `remind_days_before` set but no `due_date`.

    Raised by `TaskService` for the FR2/FR5 cross-field invariant — this
    can't be expressed as a single Pydantic field constraint for `PATCH`
    since it must hold against the task's *resulting* state, not just the
    fields present in one request.
    """

    code = "INVALID_REMINDER_CONFIGURATION"
    status_code = 422

    def __init__(self) -> None:
        super().__init__("remind_days_before requires the task to also have a due_date")


def to_error_response(exc: AppError) -> tuple[int, dict]:
    """Map a domain exception to (status_code, error-envelope body).

    Envelope shape is defined once in `core/api-design.md`:
        {"error": {"code": ..., "message": ..., "details"?: ...}}
    """
    status = exc.status_code
    if status >= 500:
        # Unexpected: log with a stack trace at ERROR and return a generic
        # message that leaks no internals (core/error-handling.md).
        logger.error("unhandled_app_error", exc_info=exc)
        code, message, details = "INTERNAL_ERROR", "An unexpected error occurred.", None
    else:
        # Expected/handled domain failure: WARNING, real message + details.
        logger.warning(exc.code.lower(), exc_info=exc)
        code = exc.code
        message = str(exc)
        details = exc.details

    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return status, body
