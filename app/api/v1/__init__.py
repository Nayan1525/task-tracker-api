"""The versioned API router.

Aggregates every resource router under the single `/v1` prefix
(frameworks/fastapi/idioms.md) so bumping the API version is one edit here.
"""

from fastapi import APIRouter

from app.api.v1.routers import comments, tasks

api_router = APIRouter(prefix="/v1")
api_router.include_router(tasks.router)
api_router.include_router(comments.router)
