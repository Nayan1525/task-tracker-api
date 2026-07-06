"""Tasks resource router — one APIRouter per resource.

Thin handlers per `core/project-structure.md`: parse input, call the
service, return. No business logic, no DB access. Handlers are plain `def`
because persistence is sync SQLAlchemy (frameworks/fastapi/idioms.md's
async-vs-sync rule) — FastAPI runs them in a threadpool.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_task_service
from app.models.task import TaskStatus
from app.schemas.error import ErrorResponse
from app.schemas.task import TaskCreate, TaskList, TaskRead, TaskUpdate
from app.services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    response: Response,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    task = service.create(payload)
    # 201 returns the resource + a Location header (core/api-design.md).
    response.headers["Location"] = f"/v1/tasks/{task.id}"
    return task


@router.get("", response_model=TaskList)
def list_tasks(
    status_: TaskStatus | None = Query(default=None, alias="status"),
    service: TaskService = Depends(get_task_service),
) -> TaskList:
    return TaskList(data=service.list(status=status_))


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    responses={404: {"model": ErrorResponse}},
)
def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    # Raises NotFoundError -> mapped to the 404 envelope by the central
    # handler; the route does not build its own error response.
    return service.get(task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    responses={404: {"model": ErrorResponse}},
)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    return service.update(task_id, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
def delete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> Response:
    service.delete(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
