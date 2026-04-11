import redis
import json
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Task

r = redis.Redis(host='localhost', port=6379, db=0)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def process_task(task_data: dict):
    db: Session = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_data["id"]).first()
        if not task:
            print(f"[Worker] Task {task_data['id']} not found in DB")
            return

        # Mark as running + stamp started_at
        task.status     = "running"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        # Publish running status via Redis so WebSocket broadcasts it
        r.publish("task_updates", json.dumps({
            "task_id": task.id,
            "status":  "running",
            "payload": task.payload,
        }))

        print(f"[Worker {task.id[:8]}] Running…")

        # Simulate real work
        time.sleep(2)

        # Mark as done + stamp completed_at
        task.status       = "done"
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        # Publish done status
        r.publish("task_updates", json.dumps({
            "task_id": task.id,
            "status":  "done",
            "payload": task.payload,
        }))

        print(f"[Worker {task.id[:8]}] Done ✓")

    except Exception as e:
        # Mark as failed if anything goes wrong
        if task:
            task.status       = "failed"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            r.publish("task_updates", json.dumps({
                "task_id": task.id,
                "status":  "failed",
            }))
        print(f"[Worker] Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("[Worker] Started — waiting for tasks…")
    while True:
        # Blocking pop — waits until a task appears in the queue
        result = r.blpop("task_queue", timeout=5)
        if result:
            _, raw = result
            task_data = json.loads(raw)
            print(f"[Worker] Picked up task {task_data['id'][:8]}…")
            process_task(task_data)
        else:
            print("[Worker] No tasks. Waiting…")