"""SQLAlchemy engine, session factory, and declarative Base.

The engine URL comes from the settings object (core/configuration-secrets.md),
never from the environment directly. `SessionLocal` produces the
request-scoped sessions injected by `app.api.deps.get_db`.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# check_same_thread=False is required for SQLite (used in tests) because
# FastAPI may run a sync `def` handler on a different thread than the one
# that created the session. Ignored for Postgres.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)


def enable_sqlite_foreign_keys(engine: Engine) -> None:
    """SQLite ignores `ON DELETE CASCADE` (and all other FK constraints)
    unless foreign key enforcement is turned on per connection. Postgres
    enforces FKs natively and needs no such hook — call this only for a
    SQLite engine."""

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_engine(settings.database_url, connect_args=_connect_args)
if settings.database_url.startswith("sqlite"):
    enable_sqlite_foreign_keys(engine)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base all ORM models inherit from."""
