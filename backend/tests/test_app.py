"""Automated tests for the Backend Service, executed by CodeBuild on every push.

To demonstrate the pipeline catching a failure (Question 3, Screenshot 1):
change EXPECTED_HEALTH_STATUS below to "broken", commit and push - the Build
stage fails. Revert to "healthy", push again - the pipeline succeeds
(Screenshot 2).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import app as flask_app

EXPECTED_HEALTH_STATUS = "healthy"


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == EXPECTED_HEALTH_STATUS


def test_list_todos_returns_list(client):
    resp = client.get("/api/todos")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_add_todo(client):
    resp = client.post("/api/todos", json={"task": "written by pytest"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["task"] == "written by pytest"
    assert body["completed"] is False


def test_add_todo_rejects_empty_task(client):
    resp = client.post("/api/todos", json={})
    assert resp.status_code == 400


def test_toggle_and_delete_todo(client):
    created = client.post("/api/todos", json={"task": "toggle me"}).get_json()
    toggled = client.put(f"/api/todos/{created['id']}")
    assert toggled.get_json()["completed"] is True
    deleted = client.delete(f"/api/todos/{created['id']}")
    assert deleted.status_code == 204


def test_synthetic_error_endpoint(client):
    resp = client.get("/api/error")
    assert resp.status_code == 500
