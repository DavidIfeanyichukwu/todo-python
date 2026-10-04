"""Backend Service - To-Do REST API (Flask).

Stores to-do items in memory, which is sufficient for this demonstration;
a production build would persist to DynamoDB or RDS via the task role.
"""
from flask import Flask, jsonify, request

app = Flask(__name__)

todos = [
    {"id": 1, "task": "Deploy the CloudFormation stack", "completed": True},
    {"id": 2, "task": "Verify the app via the ALB URL", "completed": False},
]
next_id = 3


@app.get("/health")
def health():
    """Health check used by the ALB target group."""
    return jsonify(status="healthy"), 200


@app.get("/api/health")
def api_health():
    return jsonify(status="healthy"), 200


@app.get("/api/error")
def synthetic_error():
    """Synthetic fault endpoint used to exercise monitoring (always returns HTTP 500)."""
    return jsonify(error="synthetic failure for monitoring demonstration"), 500


@app.get("/api/todos")
def list_todos():
    return jsonify(todos)


@app.post("/api/todos")
def add_todo():
    global next_id
    data = request.get_json(silent=True) or {}
    task = (data.get("task") or "").strip()
    if not task:
        return jsonify(error="task is required"), 400
    todo = {"id": next_id, "task": task, "completed": False}
    next_id += 1
    todos.append(todo)
    return jsonify(todo), 201


@app.put("/api/todos/<int:todo_id>")
def toggle_todo(todo_id):
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = not todo["completed"]
            return jsonify(todo)
    return jsonify(error="not found"), 404


@app.delete("/api/todos/<int:todo_id>")
def delete_todo(todo_id):
    global todos
    todos = [t for t in todos if t["id"] != todo_id]
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
