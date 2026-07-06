"""Unit tests for TaskService.

Fast, isolated, no DB and no app: the service is exercised against a fake
repository (frameworks/fastapi/testing.md unit tier). This is where business
logic and the not-found path are pinned exhaustively.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from app.core.exceptions import NotFoundError
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.tasks import TaskService


class FakeTaskRepository:
    """In-memory stand-in with the same interface as TaskRepository."""

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

    def list(self, *, status: TaskStatus | None = None) -> list[Task]:
        rows = list(self._rows.values())
        if status is not None:
            rows = [t for t in rows if t.status == status]
        return rows

    def get(self, task_id: int) -> Task | None:
        return self._rows.get(task_id)

    def update(self, task: Task, **fields) -> Task:
        for key, value in fields.items():
            setattr(task, key, value)
        return task

    def delete(self, task: Task) -> None:
        self._rows.pop(task.id, None)


@pytest.fixture
def service() -> TaskService:
    return TaskService(FakeTaskRepository())


def _payload(**overrides) -> TaskCreate:
    data = {"title": "Example task", "description": "Details", "priority": "medium"}
    data.update(overrides)
    return TaskCreate(**data)


def test_create_returns_persisted_task(service: TaskService) -> None:
    task = service.create(_payload(title="Saved"))
    assert task.id == 1
    assert task.title == "Saved"
    assert task.status == TaskStatus.TODO


def test_list_returns_all_created(service: TaskService) -> None:
    service.create(_payload(title="One"))
    service.create(_payload(title="Two"))
    titles = {t.title for t in service.list()}
    assert titles == {"One", "Two"}


def test_list_filters_by_status(service: TaskService) -> None:
    todo = service.create(_payload(title="Todo"))
    in_progress = service.create(_payload(title="Doing"))
    service.update(in_progress.id, TaskUpdate(status=TaskStatus.IN_PROGRESS))

    filtered = service.list(status=TaskStatus.IN_PROGRESS)
    assert [t.id for t in filtered] == [in_progress.id]
    assert todo.id not in [t.id for t in filtered]


def test_get_returns_created_task(service: TaskService) -> None:
    created = service.create(_payload())
    assert service.get(created.id).id == created.id


def test_get_missing_raises_not_found(service: TaskService) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.get(999)
    assert exc_info.value.code == "NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_update_applies_only_provided_fields(service: TaskService) -> None:
    created = service.create(_payload(title="Original", priority=TaskPriority.LOW))
    updated = service.update(created.id, TaskUpdate(status=TaskStatus.DONE))
    assert updated.status == TaskStatus.DONE
    assert updated.title == "Original"  # untouched
    assert updated.priority == TaskPriority.LOW  # untouched


def test_update_missing_raises_not_found(service: TaskService) -> None:
    with pytest.raises(NotFoundError):
        service.update(999, TaskUpdate(status=TaskStatus.DONE))


def test_update_with_no_fields_set_returns_task_unchanged(service: TaskService) -> None:
    created = service.create(_payload(title="Original", priority=TaskPriority.LOW))
    updated = service.update(created.id, TaskUpdate())
    assert updated.title == "Original"
    assert updated.priority == TaskPriority.LOW
    assert updated.status == TaskStatus.TODO


def test_delete_removes_task(service: TaskService) -> None:
    created = service.create(_payload())
    service.delete(created.id)
    with pytest.raises(NotFoundError):
        service.get(created.id)


def test_delete_missing_raises_not_found(service: TaskService) -> None:
    with pytest.raises(NotFoundError):
        service.delete(999)
