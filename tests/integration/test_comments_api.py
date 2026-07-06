"""Integration tests driving the full app via TestClient for comments.

Exercises the routers -> service -> repository -> real DB stack wired
together (frameworks/fastapi/testing.md). Covers create/list, the 404 path
for a missing task on both endpoints, the 422 validation-error envelope,
oldest-first ordering, multi-task isolation, the absent DELETE/PUT/PATCH
routes (FR7), and the FR6 end-to-end cascade-delete regression (spec §10)
driven entirely through the API rather than the repository directly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.repositories.comments import CommentRepository
from tests.factories import make_comment_payload, make_task_payload


def _create_task(client: TestClient) -> int:
    return client.post("/v1/tasks", json=make_task_payload()).json()["id"]


def test_create_comment_returns_201_and_resource(client: TestClient) -> None:
    task_id = _create_task(client)
    resp = client.post(
        f"/v1/tasks/{task_id}/comments",
        json=make_comment_payload(author="Alice", message="First comment"),
    )
    assert resp.status_code == 201
    assert resp.headers["Location"] == f"/v1/tasks/{task_id}/comments/{resp.json()['id']}"
    body = resp.json()
    assert body["task_id"] == task_id
    assert body["author"] == "Alice"
    assert body["message"] == "First comment"
    assert "id" in body
    assert "created_at" in body


def test_create_comment_response_does_not_leak_unexpected_fields(client: TestClient) -> None:
    task_id = _create_task(client)
    resp = client.post(f"/v1/tasks/{task_id}/comments", json=make_comment_payload())
    assert set(resp.json().keys()) == {"id", "task_id", "author", "message", "created_at"}


def test_create_comment_missing_task_returns_404_error_envelope(client: TestClient) -> None:
    resp = client.post("/v1/tasks/999999/comments", json=make_comment_payload())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_create_comment_blank_author_returns_422_envelope(client: TestClient) -> None:
    task_id = _create_task(client)
    resp = client.post(
        f"/v1/tasks/{task_id}/comments", json=make_comment_payload(author="")
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in body["error"]["details"]


def test_create_comment_missing_message_returns_422_envelope(client: TestClient) -> None:
    task_id = _create_task(client)
    resp = client.post(f"/v1/tasks/{task_id}/comments", json={"author": "Alice"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_comments_returns_envelope_oldest_first(client: TestClient) -> None:
    task_id = _create_task(client)
    first = client.post(
        f"/v1/tasks/{task_id}/comments",
        json=make_comment_payload(author="Alice", message="First"),
    ).json()
    second = client.post(
        f"/v1/tasks/{task_id}/comments",
        json=make_comment_payload(author="Bob", message="Second"),
    ).json()

    resp = client.get(f"/v1/tasks/{task_id}/comments")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    assert [c["id"] for c in data] == [first["id"], second["id"]]


def test_list_comments_empty_for_task_with_no_comments(client: TestClient) -> None:
    task_id = _create_task(client)
    resp = client.get(f"/v1/tasks/{task_id}/comments")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}


def test_list_comments_missing_task_returns_404_error_envelope(client: TestClient) -> None:
    resp = client.get("/v1/tasks/999999/comments")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_list_comments_isolated_per_task(client: TestClient) -> None:
    task_a = _create_task(client)
    task_b = _create_task(client)
    client.post(
        f"/v1/tasks/{task_a}/comments",
        json=make_comment_payload(author="Alice", message="For A"),
    )
    client.post(
        f"/v1/tasks/{task_b}/comments",
        json=make_comment_payload(author="Bob", message="For B"),
    )

    resp_a = client.get(f"/v1/tasks/{task_a}/comments").json()["data"]
    resp_b = client.get(f"/v1/tasks/{task_b}/comments").json()["data"]
    assert [c["message"] for c in resp_a] == ["For A"]
    assert [c["message"] for c in resp_b] == ["For B"]


def test_delete_put_patch_on_comments_collection_not_allowed(client: TestClient) -> None:
    # FR7: no route exists to update/delete a single comment. No
    # `/comments/{comment_id}` path is registered at all, so FastAPI 404s
    # there (no route matches, any method); the only registered path is the
    # collection (`POST`/`GET` only), so DELETE/PUT/PATCH against it 405
    # rather than reaching a handler — the framework default in both cases,
    # never a custom response.
    task_id = _create_task(client)
    assert client.delete(f"/v1/tasks/{task_id}/comments").status_code == 405
    assert client.put(f"/v1/tasks/{task_id}/comments").status_code == 405
    assert client.patch(f"/v1/tasks/{task_id}/comments").status_code == 405


def test_deleting_task_via_api_cascades_to_its_comments(
    client: TestClient, comment_repository: CommentRepository
) -> None:
    # Spec §10's explicit end-to-end regression: create a task and its
    # comments through the API (not the repository), delete the task through
    # the API's existing DELETE /v1/tasks/{id}, then assert directly against
    # the repository that zero comment rows remain — proving the cascade
    # fires from the real request path, not just when a repository test
    # calls TaskRepository.delete directly (see test_comment_repository.py).
    task_id = _create_task(client)
    client.post(
        f"/v1/tasks/{task_id}/comments",
        json=make_comment_payload(author="Alice", message="First"),
    )
    client.post(
        f"/v1/tasks/{task_id}/comments",
        json=make_comment_payload(author="Bob", message="Second"),
    )

    delete_resp = client.delete(f"/v1/tasks/{task_id}")
    assert delete_resp.status_code == 204

    assert comment_repository.list_for_task(task_id) == []
