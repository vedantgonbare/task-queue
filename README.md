# ⚡ TaskQueue — Distributed Worker System

A production-grade distributed task queue built with **FastAPI**, **Redis**, **PostgreSQL**, and **React**. Features real-time task monitoring via WebSockets, a live dashboard, and a background worker system — all running as a single deployable service.

> Built as a portfolio project demonstrating distributed systems, async Python, and real-time web architecture.

---

## 🎬 Demo

> 📹 [Watch Demo Video](#) ← *(paste your YouTube link here)*

![Dashboard Screenshot](docs/dashboard.png)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                       │
│              (localhost:3000 / Vercel)                      │
│                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌─────────────┐   │
│   │  Stat Cards  │    │  Task Feed   │    │ Submit Task │   │
│   │  Total/Done  │    │  Live Filter │    │ JSON Payload│   │
│   └──────────────┘    └──────────────┘    └─────────────┘   │
└────────────┬───────────────────┬──────────────────┬─────────┘
             │ HTTP REST         │ WebSocket        │ HTTP POST
             ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                 (localhost:8000 / Render)                   │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐    │ 
│  │ GET /tasks/ │  │ WebSocket    │  │  POST /tasks/    │    │
│  │ GET /tasks/ │  │ Manager      │  │  Create & Queue  │    │
│  │   {task_id} │  │ Broadcaster  │  │                  │    │
│  └─────────────┘  └──────┬───────┘  └────────┬─────────┘    │
│                           │ broadcast         │ rpush       │
│  ┌────────────────────┐   │          ┌────────▼─────────┐   │
│  │  Background Worker │◄──┼──────────│   Redis Queue    │   │
│  │  (async task loop) │   │          │  "task_queue"    │   │
│  │                    │   │          └──────────────────┘   │
│  │  pending→running   │───┼─► publish "task_updates"        │
│  │  →done/failed      │   │                                 │
│  └────────┬───────────┘   │          ┌──────────────────┐   │
│           │               └──────────│  Redis Subscriber│   │
│           │ read/write               │ (pubsub listener)│   │
│           ▼                          └──────────────────┘   │
│  ┌──────────────────┐                                       │
│  │   PostgreSQL     │                                       │
│  │   tasks table    │                                       │
│  │  id, payload,    │                                       │
│  │  status,         │                                       │
│  │  started_at,     │                                       │
│  │  completed_at    │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User clicks "Dispatch Task"
        │
        ▼
POST /tasks/  →  Save to PostgreSQL (status: pending)
        │
        ▼
Push task ID to Redis List ("task_queue")
        │
        ▼
Background Worker picks up task (blpop)
        │
        ├──► Update DB: status = "running", stamp started_at
        │
        ├──► Publish to Redis channel "task_updates"
        │              │
        │              ▼
        │    Redis Subscriber receives event
        │              │
        │              ▼
        │    WebSocket Manager broadcasts to all clients
        │              │
        │              ▼
        │    React dashboard updates task status live
        │
        ├──► Process task (simulate work)
        │
        └──► Update DB: status = "done", stamp completed_at
                       │
                       ▼
             Publish "done" event → WebSocket → React
```

---

## ✨ Features

- **Real-time task monitoring** — WebSocket connection pushes status updates instantly to the browser without polling
- **Distributed worker** — background worker runs inside FastAPI as an async task, consuming from Redis queue
- **Task Detail Modal** — click any task to see full payload, timeline (Created → Running → Done), duration, and timestamps
- **Live task feed** — filterable by All / Pending / Running / Done with animated status indicators
- **Retry tasks** — re-dispatch any task directly from the detail modal
- **Activity log** — timestamped log of every WebSocket event and HTTP call
- **Persistent storage** — all tasks stored in PostgreSQL with full history
- **Auto Swagger docs** — FastAPI generates interactive API docs at `/docs`

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | React (CRA) | Component-based UI, hooks for WebSocket state management |
| **Backend** | FastAPI (Python) | Async-first, automatic OpenAPI docs, high performance |
| **Task Queue** | Redis (List + Pub/Sub) | Atomic `blpop` for reliable task pickup, pub/sub for real-time events |
| **Database** | PostgreSQL 16 | ACID compliance, persistent task history, timestamp support |
| **Real-time** | WebSockets | Push updates to browser instantly — no polling needed |
| **ORM** | SQLAlchemy | Database-agnostic models, easy migrations |
| **Validation** | Pydantic | Request/response schema validation with zero boilerplate |

### Why Redis instead of a database queue?

PostgreSQL-based queues (like pgqueue) require polling — you repeatedly query `SELECT * FROM tasks WHERE status='pending'`. Redis `BLPOP` is a **blocking pop** — the worker sleeps until a task arrives, with zero CPU overhead. Redis also provides pub/sub for broadcasting status changes to WebSocket clients, which PostgreSQL cannot do natively.

### Why WebSockets instead of polling?

HTTP polling (e.g. `setInterval(() => fetch('/tasks'), 1000)`) creates constant unnecessary load. WebSockets maintain a persistent connection — the server pushes updates only when something changes. This makes the dashboard feel instant and reduces server load significantly at scale.

### Why FastAPI instead of Django/Flask?

FastAPI is built on Starlette and runs on an async event loop (uvicorn/asyncio). This means the worker loop, Redis subscriber, and HTTP endpoints all run concurrently in a single process without threads. Django and Flask are synchronous by default and would require additional setup (Celery, channels) to achieve the same architecture.

---

## 📁 Project Structure

```
task-queue/
│
├── app/                          # FastAPI application
│   ├── main.py                   # App entry point, worker loop, WebSocket endpoint
│   ├── database.py               # SQLAlchemy engine, session, Base
│   ├── models.py                 # Task SQLAlchemy model
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── redis_subscriber.py       # Redis pub/sub listener → WebSocket broadcaster
│   ├── websocket_manager.py      # WebSocket connection manager
│   └── routers/
│       └── tasks.py              # REST endpoints: POST /tasks/, GET /tasks/, GET /tasks/{id}
│
├── worker/
│   └── worker.py                 # Standalone worker (legacy — now merged into main.py)
│
├── frontend/                     # React application
│   └── src/
│       ├── App.js                # Root component, WebSocket logic, state management
│       ├── App.css               # Global styles
│       ├── TaskModal.jsx         # Task detail modal component
│       └── TaskModal.css         # Modal styles
│
├── .env                          # Environment variables (not committed)
├── .env.example                  # Environment variable template
├── render.yaml                   # Render deployment config
├── docker-compose.yml            # Local Redis via Docker
└── requirements.txt              # Python dependencies
```

---

## 🚀 Running Locally

### Prerequisites

- Python 3.13+
- Node.js 18+
- PostgreSQL 16
- Docker (for Redis)

### 1. Clone the repository

```bash
git clone https://github.com/vedantgonbare/task-queue.git
cd task-queue
```

### 2. Set up Python environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/taskqueue
REDIS_URL=redis://localhost:6379
```

### 4. Start PostgreSQL

```powershell
# Windows (Admin PowerShell)
& "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" start -D "C:\Program Files\PostgreSQL\16\data"
```

Create the database if it doesn't exist:
```sql
createdb -U postgres taskqueue
```

### 5. Start Redis

```bash
docker-compose up -d
```

Or if you have Redis installed locally:
```bash
redis-server
```

### 6. Start the FastAPI backend

```bash
uvicorn app.main:app --reload
```

You should see:
```
[Redis Subscriber] Listening for task updates...
[Worker] Started inside FastAPI…
INFO: Uvicorn running on http://127.0.0.1:8000
```

### 7. Start the React frontend

```bash
cd frontend
npm install
npm start
```

Open **http://localhost:3000**

---

## 📡 API Reference

Full interactive docs available at **http://localhost:8000/docs**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/tasks/` | Create and queue a new task |
| `GET` | `/tasks/` | Get all tasks (latest 50) |
| `GET` | `/tasks/{task_id}` | Get single task with full details |
| `WS` | `/ws` | WebSocket connection for real-time updates |

### Create Task

```bash
curl -X POST http://localhost:8000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"payload": "{\"type\": \"email_batch\", \"count\": 100}"}'
```

Response:
```json
{
  "id": "843deae1-5034-4f48-9203-0e32bdca...",
  "payload": "{\"type\": \"email_batch\", \"count\": 100}",
  "status": "pending",
  "created_at": "2026-04-12T10:30:00Z",
  "started_at": null,
  "completed_at": null
}
```

### WebSocket Message Format

```json
{
  "task_id": "843deae1-5034-4f48-9203-0e32bdca...",
  "status": "running",
  "payload": "{\"type\": \"email_batch\", \"count\": 100}"
}
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE tasks (
    id           VARCHAR PRIMARY KEY,      -- UUID string
    payload      TEXT NOT NULL,            -- JSON string of task data
    status       VARCHAR DEFAULT 'pending', -- pending | running | done | failed
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    started_at   TIMESTAMPTZ,              -- stamped when worker picks up task
    completed_at TIMESTAMPTZ               -- stamped when worker finishes
);
```

---

## 🔄 Task Lifecycle

```
[Created]  →  [Pending]  →  [Running]  →  [Done]
                                      ↘  [Failed]
```

| Status | Description |
|---|---|
| `pending` | Task saved to DB and pushed to Redis queue |
| `running` | Worker picked up task, `started_at` stamped |
| `done` | Task processed successfully, `completed_at` stamped |
| `failed` | Exception occurred during processing |

---

## 🧠 Key Technical Decisions

### Single-process architecture
The worker runs as an `asyncio` task inside FastAPI using `run_in_executor` for blocking Redis/DB calls. This means one `uvicorn` process handles HTTP, WebSockets, Redis pub/sub, AND task processing — making deployment simple (one service on Render vs. separate worker dyno).

### UUID task IDs
Tasks use UUID strings as primary keys instead of auto-increment integers. This prevents ID enumeration attacks and makes the system safe for future horizontal scaling where multiple instances could create tasks simultaneously without ID conflicts.

### Redis pub/sub for WebSocket broadcasting
The worker publishes status updates to a Redis channel (`task_updates`). A separate subscriber coroutine listens and broadcasts to all connected WebSocket clients. This decouples the worker from the WebSocket layer — the worker doesn't need to know about connected clients.

---

## 📈 What I Learned

- Designing async Python applications with FastAPI and asyncio
- Redis data structures: Lists for queuing (`RPUSH`/`BLPOP`), Pub/Sub for events
- WebSocket connection management and real-time state in React
- SQLAlchemy ORM with timestamp tracking
- Single-process async architecture vs. multi-process worker setups
- Production deployment considerations (CORS, env vars, connection pooling)

---

## 🗺️ Roadmap

- [ ] Worker health panel (active workers, tasks/min metrics)
- [ ] Task retry with configurable max attempts
- [ ] Task scheduling (run at specific time)
- [ ] Multiple queue priorities (high/medium/low)
- [ ] Deploy to Render + Vercel with Upstash Redis

---

## 👨‍💻 Author

**Vedant Gonbare**
- GitHub: [@vedantgonbare](https://github.com/vedantgonbare)

---

## 📄 License

MIT License — feel free to use this project as a reference or starting point.