"""Shared test fixtures (frameworks/fastapi/testing.md).

Provides a real in-memory SQLite session per test and a TestClient whose
`get_db` dependency is overridden to use that same session — so the
repository is exercised for real (not mocked) and assertions the test makes
against the DB see what a request wrote.

SQLite stands in for Postgres in tests (same SQLAlchemy Core types are used
throughout the model, so behavior matches); point DATABASE_URL at a real
Postgres instance to run the suite against it if needed.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.session import Base, enable_sqlite_foreign_keys
from app.main import create_app
from app.repositories.comments import CommentRepository
from app.repositories.tasks import TaskRepository


@pytest.fixture
def db_session() -> Iterator[Session]:
    # A single shared in-memory connection (StaticPool) kept alive across the
    # request threadpool; check_same_thread=False for SQLite + threads.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Without this, SQLite silently ignores FK constraints (including
    # comments.task_id's ON DELETE CASCADE) and the test suite would pass
    # vacuously — see spec §13's cross-database risk.
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def repository(db_session: Session) -> TaskRepository:
    return TaskRepository(db_session)


@pytest.fixture
def comment_repository(db_session: Session) -> CommentRepository:
    return CommentRepository(db_session)


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # The app's startup lifespan calls init_db() against the *production*
    # engine (bound to DATABASE_URL, which defaults to Postgres) — harmless
    # for the SQLite-default bookmarks example this pattern comes from, but
    # a real Postgres connection attempt here. The test DB schema is already
    # created on the in-memory SQLite engine by `db_session`, so no-op it.
    monkeypatch.setattr("app.main.init_db", lambda: None)
    app = create_app()
    # Hand every request the same session the test holds.
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
