"""Frontend Service - simple web application (Flask).

Serves the To-Do List page. The browser calls the Backend Service at /api/*
through the Application Load Balancer's path-based routing, so both services
share one origin and no CORS configuration is required.
"""
from flask import Flask, Response

app = Flask(__name__)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>To-Do List — Microservices Demo</title>
<style>
  :root { --accent:#1F4E79; }
  * { box-sizing:border-box; font-family:'Segoe UI',Arial,sans-serif; }
  body { margin:0; background:#f4f6f9; color:#222; }
  header { background:var(--accent); color:#fff; padding:22px 0; text-align:center; }
  header h1 { margin:0; font-size:1.6rem; }
  header p { margin:6px 0 0; font-size:.9rem; opacity:.85; }
  main { max-width:560px; margin:34px auto; padding:0 16px; }
  form { display:flex; gap:10px; margin-bottom:22px; }
  input[type=text] { flex:1; padding:12px 14px; border:1px solid #c8d0da; border-radius:8px; font-size:1rem; }
  button { background:var(--accent); color:#fff; border:none; border-radius:8px; padding:12px 18px; font-size:1rem; cursor:pointer; }
  ul { list-style:none; padding:0; margin:0; }
  li { background:#fff; border:1px solid #e1e6ec; border-radius:8px; padding:12px 14px; margin-bottom:10px;
       display:flex; align-items:center; gap:12px; }
  li.done span.task { text-decoration:line-through; color:#8a95a3; }
  li span.task { flex:1; cursor:pointer; }
  li button.del { background:#c7131f; padding:6px 12px; font-size:.85rem; }
  .status { text-align:center; color:#6b7684; font-size:.85rem; margin-top:26px; }
</style>
</head>
<body>
<header>
  <h1>To-Do List</h1>
  <p>Frontend Service (Flask) &rarr; ALB /api/* &rarr; Backend Service (Flask API) on ECS Fargate</p>
</header>
<main>
  <form id="addForm">
    <input type="text" id="taskText" placeholder="What needs doing?" required>
    <button type="submit">Add</button>
  </form>
  <ul id="list"></ul>
  <p class="status" id="status">Loading&hellip;</p>
</main>
<script>
const list = document.getElementById('list');
const status = document.getElementById('status');

async function load() {
  try {
    const res = await fetch('/api/todos');
    const todos = await res.json();
    list.innerHTML = '';
    todos.forEach(t => {
      const li = document.createElement('li');
      if (t.completed) li.className = 'done';
      const span = document.createElement('span');
      span.className = 'task';
      span.textContent = t.task;
      span.title = 'Click to toggle done';
      span.onclick = async () => { await fetch('/api/todos/' + t.id, { method:'PUT' }); load(); };
      const del = document.createElement('button');
      del.className = 'del';
      del.textContent = 'Delete';
      del.onclick = async () => { await fetch('/api/todos/' + t.id, { method:'DELETE' }); load(); };
      li.append(span, del);
      list.appendChild(li);
    });
    status.textContent = todos.length + ' item(s) — served live by the Backend API';
  } catch (e) {
    status.textContent = 'Backend API unreachable: ' + e.message;
  }
}

document.getElementById('addForm').onsubmit = async (e) => {
  e.preventDefault();
  const input = document.getElementById('taskText');
  await fetch('/api/todos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task: input.value })
  });
  input.value = '';
  load();
};

load();
</script>
</body>
</html>"""


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.get("/health")
def health():
    """Health check used by the ALB target group."""
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
