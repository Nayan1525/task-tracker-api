"""The Comment ORM model — persistence detail, never returned to a client.

A response is always mediated by a schema (`app.schemas.comment`) per
`core/api-design.md`; the model is an implementation detail per
`core/project-structure.md`.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.timezone.utc)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        # CommentRepository.list_for_task filters on task_id; without this,
        # that query is a sequential scan once the table has real row counts.
        Index("ix_comments_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ondelete="CASCADE" is the DB-level enforcement of "comments cannot
    # outlive their task" (spec NFR §6) — see app.db.session for the SQLite
    # pragma required for this to actually fire in tests/local dev.
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
