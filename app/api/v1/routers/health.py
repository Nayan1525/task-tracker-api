"""Liveness and readiness endpoints.

Two distinct endpoints per `core/logging-observability.md`: `/health` says
"the process is up" (no dependency checks); `/ready` says "this instance can
serve traffic" (checks the DB). These live outside the `/v1` prefix — they
are operational, not part of the versioned API contract.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter(tags=["ops"])


@router.get("/health")
def health() -> dict:
    """Liveness: 200 if the process can respond at all. No dependency checks."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: 200 only if the DB is reachable, else 503."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 -- readiness must report, not raise
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}
