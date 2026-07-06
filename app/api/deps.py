"""Shared FastAPI dependency providers.

This is where `core/project-structure.md`'s layering is physically wired per
request: a request-scoped db session -> repository -> service. Routes depend
on the service, not on the session or repository (frameworks/fastapi/idioms.md).
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.repositories.tasks import TaskRepository
from app.services.tasks import TaskService


def get_db() -> Iterator[Session]:
    """Request-scoped session; closed in `finally` even if the handler errors."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(TaskRepository(db))
