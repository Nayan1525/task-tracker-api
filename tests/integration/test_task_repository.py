"""Integration tests for TaskRepository against a real (test) DB session.

Per core/testing-strategy.md, the integration tier uses a real database
rather than mocking the thing under test — this proves the actual
round-trip, not that a mock behaves as told.
"""

from __future__ import annotations

from app.models.task import TaskPriority, TaskStatus
from app.repositories.tasks import TaskRepository


def test_create_then_get_round_trips(repository: TaskRepository) -> None:
    created = repository.create(
        title="A", description="desc", priority=TaskPriority.HIGH, due_date=None
    )
    fetched = repository.get(created.id)
    assert fetched is not None
    assert fetched.title == "A"
    assert fetched.status == TaskStatus.TODO
    assert fetched.priority == TaskPriority.HIGH
    assert fetched.created_at is not None


def test_get_missing_returns_none(repository: TaskRepository) -> None:
    assert repository.get(12345) is None


def test_list_orders_newest_first(repository: TaskRepository) -> None:
    first = repository.create(
        title="A", description=None, priority=TaskPriority.MEDIUM, due_date=None
    )
    second = repository.create(
        title="B", description=None, priority=TaskPriority.MEDIUM, due_date=None
    )
    ids = [t.id for t in repository.list()]
    # Newest (higher id / later created_at) first.
    assert ids[0] == second.id
    assert first.id in ids


def test_list_filters_by_status(repository: TaskRepository) -> None:
    todo = repository.create(
        title="Todo", description=None, priority=TaskPriority.MEDIUM, due_date=None
    )
    done = repository.create(
        title="Done", description=None, priority=TaskPriority.MEDIUM, due_date=None
    )
    repository.update(done, status=TaskStatus.DONE)

    filtered = repository.list(status=TaskStatus.DONE)
    assert [t.id for t in filtered] == [done.id]
    assert todo.id not in [t.id for t in filtered]


def test_update_persists_changes(repository: TaskRepository) -> None:
    created = repository.create(
        title="A", description=None, priority=TaskPriority.LOW, due_date=None
    )
    updated = repository.update(created, status=TaskStatus.IN_PROGRESS)
    assert updated.status == TaskStatus.IN_PROGRESS
    assert repository.get(created.id).status == TaskStatus.IN_PROGRESS


def test_delete_removes_row(repository: TaskRepository) -> None:
    created = repository.create(
        title="A", description=None, priority=TaskPriority.MEDIUM, due_date=None
    )
    repository.delete(created)
    assert repository.get(created.id) is None
