"""Pydantic v2 request/response schemas for the Comment resource.

Separate input (`CommentCreate`) and output (`CommentRead`/`CommentList`)
schemas per `frameworks/fastapi/idioms.md`, mirroring `app/schemas/task.py`:
inputs have no server-assigned fields, and the output allow-lists exactly
what clients see so no ORM internals leak (`core/api-design.md`).
"""

from __future__ import annotations

import datetime as _dt

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Request body for POST /v1/tasks/{id}/comments — validated at the boundary."""

    author: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class CommentRead(BaseModel):
    """Response body for a single comment.

    `from_attributes=True` lets FastAPI serialize a SQLAlchemy row directly
    via `response_model`, applying this schema as the field allow-list.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author: str
    message: str
    created_at: _dt.datetime


class CommentList(BaseModel):
    """Response body for GET /v1/tasks/{id}/comments (the collection)."""

    data: list[CommentRead]
