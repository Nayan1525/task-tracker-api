"""The error-envelope response model.

Documents the `core/api-design.md` error shape in the OpenAPI schema so
clients see the contract they'll get from every failing endpoint. The
actual envelope is produced by `app.core.exceptions.to_error_response`.
"""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
