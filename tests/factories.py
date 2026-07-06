"""Test-data factories (core/testing-strategy.md).

Two shapes: a payload factory for driving the API via `client.post(json=...)`,
and a model factory for seeding the DB directly in repository/integration
tests. Each has sane defaults; a test overrides only what it cares about.
"""

from __future__ import annotations

from app.models.task import Task, TaskPriority, TaskStatus


def make_task_payload(**overrides) -> dict:
    return {
        "title": "Write the quarterly report",
        "description": "Summarize progress for stakeholders.",
        "priority": "medium",
        **overrides,
    }


def make_task_model(**overrides) -> Task:
    defaults = dict(
        title="Write the quarterly report",
        description="Summarize progress for stakeholders.",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    return Task(**{**defaults, **overrides})
