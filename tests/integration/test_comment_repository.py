"""Integration tests for CommentRepository against a real (test) DB session.

Per core/testing-strategy.md, the integration tier uses a real database
rather than mocking the thing under test. This file specifically proves the
DB-level `ON DELETE CASCADE` (spec NFR §6) actually fires under the same
SQLite engine/config the full suite uses, per spec §13's cross-database risk.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.task import TaskPriority
from app.repositories.comments import CommentRepository
from app.repositories.tasks import TaskRepository


def _make_task(repository: TaskRepository):
    return repository.create(
        title="A", description=None, priority=TaskPriority.MEDIUM, due_date=None
    )


def test_list_for_task_with_no_comments_returns_empty_list(
    repository: TaskRepository, comment_repository: CommentRepository
) -> None:
    task = _make_task(repository)
    assert comment_repository.list_for_task(task.id) == []


def test_list_for_task_returns_comments_in_creation_order(
    repository: TaskRepository, comment_repository: CommentRepository
) -> None:
    task = _make_task(repository)
    first = comment_repository.create(task_id=task.id, author="Alice", message="First")
    second = comment_repository.create(task_id=task.id, author="Bob", message="Second")

    comments = comment_repository.list_for_task(task.id)
    assert [c.id for c in comments] == [first.id, second.id]


def test_deleting_task_cascades_to_its_comments(
    repository: TaskRepository,
    comment_repository: CommentRepository,
    db_session: Session,
) -> None:
    task = _make_task(repository)
    comment_repository.create(task_id=task.id, author="Alice", message="First")
    comment_repository.create(task_id=task.id, author="Bob", message="Second")

    repository.delete(task)

    remaining = db_session.execute(
        select(Comment).where(Comment.task_id == task.id)
    ).scalars().all()
    assert remaining == []


def test_inserting_comment_for_missing_task_raises_integrity_error(
    db_session: Session,
) -> None:
    orphan = Comment(task_id=999_999, author="Alice", message="Orphan")
    db_session.add(orphan)
    with pytest.raises(IntegrityError):
        db_session.commit()
