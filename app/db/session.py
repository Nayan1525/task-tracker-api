"""SQLAlchemy engine, session factory, and declarative Base.

The engine URL comes from the settings object (core/configuration-secrets.md),
never from the environment directly. `SessionLocal` produces the
request-scoped sessions injected by `app.api.deps.get_db`.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# check_same_thread=False is required for SQLite (used in tests) because
# FastAPI may run a sync `def` handler on a different thread than the one
# that created the session. Ignored for Postgres.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base all ORM models inherit from."""


def init_db() -> None:
    """Create tables. Fine for a sample app; a real service runs migrations
    (e.g. Alembic) instead — see README."""
    # Import models so they're registered on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
