"""Integration tests driving the full app via TestClient.

Exercises the routers -> service -> repository -> real DB stack wired
together (frameworks/fastapi/testing.md). Covers create/list/get/update/
delete and the error-envelope contract from core/api-design.md, including
validation.
"""

from __future__ import annotations

import datetime as _dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import make_task_model, make_task_payload


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
        "remind_days_before",
        "created_at",
        "updated_at",
    }


# --- Reminder configuration (remind_days_before, FR2/FR5) -----------------


def test_create_with_due_date_and_reminder_returns_201(client: TestClient) -> None:
    resp = client.post(
        "/v1/tasks",
        json=make_task_payload(due_date="2026-12-01", remind_days_before=3),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["due_date"] == "2026-12-01"
    assert body["remind_days_before"] == 3


def test_create_with_reminder_but_no_due_date_returns_422(client: TestClient) -> None:
    resp = client.post("/v1/tasks", json=make_task_payload(remind_days_before=3))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REMINDER_CONFIGURATION"


def test_patch_can_set_read_back_and_clear_reminder(client: TestClient) -> None:
    created = client.post(
        "/v1/tasks", json=make_task_payload(due_date="2026-12-01")
    ).json()
    assert created["remind_days_before"] is None

    set_resp = client.patch(
        f"/v1/tasks/{created['id']}", json={"remind_days_before": 5}
    )
    assert set_resp.status_code == 200
    assert set_resp.json()["remind_days_before"] == 5

    get_resp = client.get(f"/v1/tasks/{created['id']}")
    assert get_resp.json()["remind_days_before"] == 5

    clear_resp = client.patch(
        f"/v1/tasks/{created['id']}", json={"remind_days_before": None}
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["remind_days_before"] is None


def test_patch_removing_due_date_with_existing_reminder_returns_422(
    client: TestClient,
) -> None:
    created = client.post(
        "/v1/tasks",
        json=make_task_payload(due_date="2026-12-01", remind_days_before=3),
    ).json()
    resp = client.patch(f"/v1/tasks/{created['id']}", json={"due_date": None})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REMINDER_CONFIGURATION"


def test_patch_removing_due_date_and_clearing_reminder_returns_200(
    client: TestClient,
) -> None:
    created = client.post(
        "/v1/tasks",
        json=make_task_payload(due_date="2026-12-01", remind_days_before=3),
    ).json()
    resp = client.patch(
        f"/v1/tasks/{created['id']}",
        json={"due_date": None, "remind_days_before": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["due_date"] is None
    assert body["remind_days_before"] is None


def test_get_endpoints_include_reminder_field_for_task_without_one(
    client: TestClient, db_session: Session
) -> None:
    # Seeded directly, bypassing the API — proves pre-existing/unrelated
    # tasks (no remind_days_before ever set) still round-trip as null.
    task = make_task_model(due_date=_dt.date(2026, 12, 1))
    db_session.add(task)
    db_session.commit()

    list_resp = client.get("/v1/tasks")
    assert list_resp.status_code == 200
    listed = next(t for t in list_resp.json()["data"] if t["id"] == task.id)
    assert listed["remind_days_before"] is None

    get_resp = client.get(f"/v1/tasks/{task.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["remind_days_before"] is None


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
