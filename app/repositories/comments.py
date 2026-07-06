"""Data access for comments — the only layer that talks to the database.

Per `core/project-structure.md`, this is the sole place importing SQLAlchemy
query APIs. Services depend on this class, not on the session directly, so
the persistence mechanism can change without touching business logic.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment


class CommentRepository:
    """Persistence for the Comment resource, scoped to a parent task."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, *, task_id: int, author: str, message: str) -> Comment:
        comment = Comment(task_id=task_id, author=author, message=message)
        self._db.add(comment)
        self._db.commit()
        self._db.refresh(comment)
        return comment

    def list_for_task(self, task_id: int) -> list[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
        return list(self._db.execute(stmt).scalars().all())
