"""Unit tests for CommentService.

Fast, isolated, no DB and no app: the service is exercised against a fake
comment repository plus a `TaskService` backed by a fake task repository
(frameworks/fastapi/testing.md unit tier), mirroring
`tests/unit/test_task_service.py`'s pattern.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from app.core.exceptions import NotFoundError
from app.models.comment import Comment
from app.models.task import Task, TaskStatus
from app.schemas.comment import CommentCreate
from app.schemas.task import TaskCreate
from app.services.comments import CommentService
from app.services.tasks import TaskService


class FakeTaskRepository:
    """Minimal in-memory TaskRepository stand-in — only what CommentService needs."""

    def __init__(self) -> None:
        self._rows: dict[int, Task] = {}
        self._next_id = 1

    def create(self, *, title, description, priority, due_date) -> Task:
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        task = Task(
            id=self._next_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            due_date=due_date,
            created_at=now,
            updated_at=now,
        )
        self._rows[self._next_id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Task | None:
        return self._rows.get(task_id)


class FakeCommentRepository:
    """In-memory stand-in with the same interface as CommentRepository."""

    def __init__(self) -> None:
        self._rows: dict[int, Comment] = {}
        self._next_id = 1

    def create(self, *, task_id: int, author: str, message: str) -> Comment:
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        comment = Comment(
            id=self._next_id,
            task_id=task_id,
            author=author,
            message=message,
            created_at=now,
        )
        self._rows[self._next_id] = comment
        self._next_id += 1
        return comment

    def list_for_task(self, task_id: int) -> list[Comment]:
        return [c for c in self._rows.values() if c.task_id == task_id]


@pytest.fixture
def task_service() -> TaskService:
    return TaskService(FakeTaskRepository())


@pytest.fixture
def service(task_service: TaskService) -> CommentService:
    return CommentService(task_service, FakeCommentRepository())


def _task_payload(**overrides) -> TaskCreate:
    data = {"title": "Example task", "description": "Details", "priority": "medium"}
    data.update(overrides)
    return TaskCreate(**data)


def _comment_payload(**overrides) -> CommentCreate:
    data = {"author": "Jane Doe", "message": "Looks good to me."}
    data.update(overrides)
    return CommentCreate(**data)


def test_create_returns_persisted_comment(
    service: CommentService, task_service: TaskService
) -> None:
    task = task_service.create(_task_payload())
    comment = service.create(task.id, _comment_payload(author="Alice", message="First!"))
    assert comment.id == 1
    assert comment.task_id == task.id
    assert comment.author == "Alice"
    assert comment.message == "First!"
    assert comment.created_at is not None


def test_create_missing_task_raises_not_found(service: CommentService) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.create(999, _comment_payload())
    assert exc_info.value.code == "NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_list_returns_comments_in_insertion_order(
    service: CommentService, task_service: TaskService
) -> None:
    task = task_service.create(_task_payload())
    first = service.create(task.id, _comment_payload(message="First"))
    second = service.create(task.id, _comment_payload(message="Second"))

    comments = service.list(task.id)
    assert [c.id for c in comments] == [first.id, second.id]


def test_list_excludes_comments_from_other_tasks(
    service: CommentService, task_service: TaskService
) -> None:
    task_a = task_service.create(_task_payload(title="A"))
    task_b = task_service.create(_task_payload(title="B"))
    service.create(task_a.id, _comment_payload(message="For A"))
    service.create(task_b.id, _comment_payload(message="For B"))

    comments = service.list(task_a.id)
    assert [c.message for c in comments] == ["For A"]


def test_list_missing_task_raises_not_found(service: CommentService) -> None:
    with pytest.raises(NotFoundError):
        service.list(999)


def test_list_on_task_with_no_comments_returns_empty_list(
    service: CommentService, task_service: TaskService
) -> None:
    task = task_service.create(_task_payload())
    assert service.list(task.id) == []
