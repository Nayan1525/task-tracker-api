"""Structured (JSON) logging with a per-request correlation ID.

Implements `core/logging-observability.md`: JSON log lines keyed by a short
stable `event` name, and a `request_id` context var injected into every
record by a logging filter (not passed manually to every call).
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
from contextvars import ContextVar

# Set per request by the request-id middleware in main.py; read by the filter.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects the current request_id onto every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


# Attributes that are always present on a LogRecord; anything else passed via
# logger.info(..., extra={...}) is treated as structured context and included.
_STANDARD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"request_id", "message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Renders a log record as a single JSON object.

    The `event` name is the log message (kept short/stable, like the API
    error `code`); `extra={...}` fields are merged in as structured context.
    Never log secrets or PII here — see `core/logging-observability.md`.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": _dt.datetime.fromtimestamp(
                record.created, tz=_dt.timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "logger": record.name,
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Wire the root logger to emit JSON with the request-id filter attached.

    Called once from the composition root (main.py) at startup.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
