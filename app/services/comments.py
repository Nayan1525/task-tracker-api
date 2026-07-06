"""Business logic for comments.

Framework-agnostic per `core/project-structure.md`: no FastAPI imports, so
this is callable from a script, worker, or unit test without an app. Raises
domain exceptions (`AppError` subclasses), never `HTTPException` — the
central handler maps those to the error envelope (`core/error-handling.md`).

Existence of the owning task (FR2/FR5) is checked via `TaskService.get`,
reusing the `NotFoundError` it already raises rather than duplicating a
task-existence check against `TaskRepository` directly.
"""

from __future__ import annotations

import logging

from app.models.comment import Comment
from app.repositories.comments import CommentRepository
from app.schemas.comment import CommentCreate
from app.services.tasks import TaskService

logger = logging.getLogger(__name__)


class CommentService:
    def __init__(self, task_service: TaskService, comment_repository: CommentRepository) -> None:
        self._task_service = task_service
        self._repository = comment_repository

    def create(self, task_id: int, payload: CommentCreate) -> Comment:
        self._task_service.get(task_id)  # raises NotFoundError if absent
        comment = self._repository.create(
            task_id=task_id, author=payload.author, message=payload.message
        )
        logger.info("comment_created", extra={"task_id": task_id, "comment_id": comment.id})
        return comment

    def list(self, task_id: int) -> list[Comment]:
        self._task_service.get(task_id)  # raises NotFoundError if absent
        return self._repository.list_for_task(task_id)
