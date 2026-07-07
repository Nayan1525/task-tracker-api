"""Business logic for tasks.

Framework-agnostic per `core/project-structure.md`: no FastAPI imports, so
this is callable from a script, worker, or unit test without an app. Raises
domain exceptions (`AppError` subclasses), never `HTTPException` — the
central handler maps those to the error envelope (`core/error-handling.md`).
"""

from __future__ import annotations

import logging

from app.core.exceptions import InvalidReminderConfigurationError, NotFoundError
from app.models.task import Task, TaskStatus
from app.repositories.tasks import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create(self, payload: TaskCreate) -> Task:
        # FR2: a reminder can only be set on a task that has a due_date.
        if payload.remind_days_before is not None and payload.due_date is None:
            raise InvalidReminderConfigurationError()
        task = self._repository.create(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            due_date=payload.due_date,
            remind_days_before=payload.remind_days_before,
        )
        logger.info("task_created", extra={"task_id": task.id})
        return task

    def list(self, *, status: TaskStatus | None = None) -> list[Task]:
        return self._repository.list(status=status)

    def get(self, task_id: int) -> Task:
        task = self._repository.get(task_id)
        if task is None:
            raise NotFoundError("task", task_id)
        return task

    def update(self, task_id: int, payload: TaskUpdate) -> Task:
        task = self.get(task_id)  # raises NotFoundError if absent
        # Only apply fields the client actually sent — an omitted field
        # must not overwrite existing data with None.
        fields = payload.model_dump(exclude_unset=True)
        if not fields:
            return task
        # FR2/FR5: validate against the task's *resulting* state, not just
        # the fields present in this request — a field omitted here still
        # carries its current value forward.
        effective_due_date = fields.get("due_date", task.due_date)
        effective_remind_days_before = fields.get(
            "remind_days_before", task.remind_days_before
        )
        if effective_remind_days_before is not None and effective_due_date is None:
            raise InvalidReminderConfigurationError()
        updated = self._repository.update(task, **fields)
        logger.info("task_updated", extra={"task_id": task_id, "fields": list(fields)})
        return updated

    def delete(self, task_id: int) -> None:
        task = self.get(task_id)  # raises NotFoundError if absent
        self._repository.delete(task)
        logger.info("task_deleted", extra={"task_id": task_id})
