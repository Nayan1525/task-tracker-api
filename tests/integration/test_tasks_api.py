"""Integration tests driving the full app via TestClient.

Exercises the routers -> service -> repository -> real DB stack wired
together (frameworks/fastapi/testing.md). Covers create/list/get/update/
delete and the error-envelope contract from core/api-design.md, including
validation.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.factories import make_task_payload


def test_create_task_returns_201_and_resource(client: TestClient) -> None:
    resp = client.post("/v1/tasks", json=make_task_payload(title="Saved"))
    assert resp.status_code == 201
    assert resp.headers["Location"].startswith("/v1/tasks/")
    body = resp.json()
    assert body["id"] >= 1
    assert body["title"] == "Saved"
    assert body["status"] == "todo"
    assert body["priority"] == "medium"
    assert "created_at" in body
    assert "updated_at" in body


def test_list_tasks_returns_envelope(client: TestClient) -> None:
    client.post("/v1/tasks", json=make_task_payload(title="One"))
    client.post("/v1/tasks", json=make_task_payload(title="Two"))
    resp = client.get("/v1/tasks")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {t["title"] for t in data} == {"One", "Two"}


def test_list_tasks_filters_by_status(client: TestClient) -> None:
    first = client.post("/v1/tasks", json=make_task_payload(title="Todo")).json()
    second = client.post("/v1/tasks", json=make_task_payload(title="Doing")).json()
    client.patch(f"/v1/tasks/{second['id']}", json={"status": "in_progress"})

    resp = client.get("/v1/tasks", params={"status": "in_progress"})
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()["data"]]
    assert ids == [second["id"]]
    assert first["id"] not in ids


def test_get_task_returns_it(client: TestClient) -> None:
    created = client.post("/v1/tasks", json=make_task_payload()).json()
    resp = client.get(f"/v1/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_update_task_status(client: TestClient) -> None:
    created = client.post("/v1/tasks", json=make_task_payload()).json()
    resp = client.patch(f"/v1/tasks/{created['id']}", json={"status": "done"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["title"] == created["title"]  # untouched fields preserved


def test_update_missing_returns_404_error_envelope(client: TestClient) -> None:
    resp = client.patch("/v1/tasks/999999", json={"status": "done"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_delete_task_returns_204_then_404(client: TestClient) -> None:
    created = client.post("/v1/tasks", json=make_task_payload()).json()
    del_resp = client.delete(f"/v1/tasks/{created['id']}")
    assert del_resp.status_code == 204
    # Deleting is effective: a subsequent GET is now 404.
    assert client.get(f"/v1/tasks/{created['id']}").status_code == 404


def test_get_missing_returns_404_error_envelope(client: TestClient) -> None:
    resp = client.get("/v1/tasks/999999")
    assert resp.status_code == 404
    body = resp.json()
    # Exact envelope shape from core/api-design.md.
    assert set(body.keys()) == {"error"}
    assert body["error"]["code"] == "NOT_FOUND"
    assert "999999" in body["error"]["message"]
    assert body["error"]["details"]["resource"] == "task"


def test_delete_missing_returns_404_error_envelope(client: TestClient) -> None:
    resp = client.delete("/v1/tasks/999999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_invalid_create_body_returns_422_envelope(client: TestClient) -> None:
    # Missing required `title` — should never reach the service; FastAPI
    # validation fails at the boundary.
    resp = client.post("/v1/tasks", json={"priority": "not-a-priority"})
    assert resp.status_code == 422
    body = resp.json()
    # Validation errors use the SAME envelope as every other error.
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in body["error"]["details"]


def test_response_does_not_leak_unexpected_fields(client: TestClient) -> None:
    created = client.post("/v1/tasks", json=make_task_payload()).json()
    # Output schema allow-lists exactly these fields (core/api-design.md).
    assert set(created.keys()) == {
        "id",
        "title",
        "description",
        "status",
        "priority",
        "due_date",
        "created_at",
        "updated_at",
    }


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ready_endpoint(client: TestClient) -> None:
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_request_id_header_returned(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.headers.get("X-Request-ID")
