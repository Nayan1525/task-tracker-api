"""Pydantic v2 request/response schemas for the Task resource.

Separate input (`TaskCreate`, `TaskUpdate`) and output (`TaskRead`) schemas
per `frameworks/fastapi/idioms.md`: inputs have no server-assigned fields,
and the output allow-lists exactly what clients see so no ORM internals leak
(`core/api-design.md`).
"""

from __future__ import annotations

import datetime as _dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Request body for POST /v1/tasks — validated at the boundary."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: _dt.date | None = None
    remind_days_before: int | None = Field(
        default=None,
        ge=0,
        le=3650,
        description=(
            "Number of days before due_date to remind on. Requires due_date to "
            "also be set. Configuring this does not send any notification — no "
            "delivery mechanism exists yet."
        ),
    )


class TaskUpdate(BaseModel):
    """Request body for PATCH /v1/tasks/{id} — every field optional.

    Only fields explicitly set by the client are applied (`model_fields_set`
    in the service), so omitting a field leaves it unchanged.
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: _dt.date | None = None
    remind_days_before: int | None = Field(
        default=None,
        ge=0,
        le=3650,
        description=(
            "Number of days before due_date to remind on. Requires due_date to "
            "also be set. Configuring this does not send any notification — no "
            "delivery mechanism exists yet."
        ),
    )


class TaskRead(BaseModel):
    """Response body for a single task.

    `from_attributes=True` lets FastAPI serialize a SQLAlchemy row directly
    via `response_model`, applying this schema as the field allow-list.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: _dt.date | None
    remind_days_before: int | None = Field(
        description=(
            "Number of days before due_date to remind on, null if no reminder "
            "is configured. Configuring this does not send any notification — "
            "no delivery mechanism exists yet."
        ),
    )
    created_at: _dt.datetime
    updated_at: _dt.datetime


class TaskList(BaseModel):
    """Response body for GET /v1/tasks (the collection)."""

    data: list[TaskRead]
