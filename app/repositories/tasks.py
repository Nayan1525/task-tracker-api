"""Data access for tasks — the only layer that talks to the database.

Per `core/project-structure.md`, this is the sole place importing SQLAlchemy
query APIs. Services depend on this class, not on the session directly, so
the persistence mechanism can change without touching business logic.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus


class TaskRepository:
    """CRUD persistence for the Task resource."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        title: str,
        description: str | None,
        priority: TaskPriority,
        due_date: _dt.date | None,
        remind_days_before: int | None = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            remind_days_before=remind_days_before,
        )
        self._db.add(task)
        self._db.commit()
        self._db.refresh(task)
        return task

    def list(self, *, status: TaskStatus | None = None) -> list[Task]:
        stmt = select(Task)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.created_at.desc(), Task.id.desc())
        return list(self._db.execute(stmt).scalars().all())

    def get(self, task_id: int) -> Task | None:
        return self._db.get(Task, task_id)

    def update(self, task: Task, **fields: object) -> Task:
        for key, value in fields.items():
            setattr(task, key, value)
        self._db.commit()
        self._db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self._db.delete(task)
        self._db.commit()
