import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, redis_client
from app.models import Task
import time

QUEUE_NAME = "task_queue"

def process_task(payload: str) -> str:
    # Simulate real work taking 2 seconds
    # Later this will send emails, resize images, call APIs etc.
    time.sleep(2)
    return f"Processed: {payload}"

def run_worker():
    worker_id = os.getpid()  # unique ID = process ID
    print(f"[Worker {worker_id}] Started. Waiting for tasks...")

    while True:
        # brpop = Blocking Right Pop
        # Waits up to 5 seconds for a task, returns None if nothing arrives
        task_data = redis_client.brpop(QUEUE_NAME, timeout=5)

        if task_data is None:
            print(f"[Worker {worker_id}] No tasks in queue. Waiting...")
            continue

        # task_data = ("task_queue", "some-uuid-here")
        # We only need the second element — the task ID
        _, task_id = task_data
        print(f"[Worker {worker_id}] Picked up task: {task_id}")

        db = SessionLocal()
        try:
            # 1. Fetch task from PostgreSQL
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                print(f"[Worker {worker_id}] Task {task_id} not found in DB. Skipping.")
                continue

            # 2. Mark as processing
            task.status = "processing"
            db.commit()
            print(f"[Worker {worker_id}] Task {task_id} status → processing")

            # 3. Do the actual work
            result = process_task(task.payload)

            # 4. Mark as done + save result
            task.status = "done"
            task.result = result
            db.commit()
            print(f"[Worker {worker_id}] Task {task_id} status → done")
            print(f"[Worker {worker_id}] Result: {result}")

        except Exception as e:
            # If anything goes wrong, mark as failed
            print(f"[Worker {worker_id}] ERROR on task {task_id}: {e}")
            if task:
                task.status = "failed"
                db.commit()

        finally:
            # Always close the DB session — prevents connection leaks
            db.close()

if __name__ == "__main__":
    run_worker()