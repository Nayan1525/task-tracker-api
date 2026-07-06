"""Comments resource router — nested one level under a task.

Thin handlers per `core/project-structure.md`: parse input, call the
service, return. No business logic, no DB/repository access. Handlers are
plain `def` for the same sync-SQLAlchemy reason as
`app/api/v1/routers/tasks.py`. No `PUT`/`PATCH`/`DELETE` route is defined
(FR7) — the framework's default 405 applies to those methods.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_comment_service
from app.schemas.comment import CommentCreate, CommentList, CommentRead
from app.schemas.error import ErrorResponse
from app.services.comments import CommentService

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


@router.post(
    "",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
)
def create_comment(
    task_id: int,
    payload: CommentCreate,
    response: Response,
    service: CommentService = Depends(get_comment_service),
) -> CommentRead:
    # Raises NotFoundError -> mapped to the 404 envelope by the central
    # handler; the route does not build its own error response.
    comment = service.create(task_id, payload)
    response.headers["Location"] = f"/v1/tasks/{task_id}/comments/{comment.id}"
    return comment


@router.get(
    "",
    response_model=CommentList,
    responses={404: {"model": ErrorResponse}},
)
def list_comments(
    task_id: int,
    service: CommentService = Depends(get_comment_service),
) -> CommentList:
    return CommentList(data=service.list(task_id))
