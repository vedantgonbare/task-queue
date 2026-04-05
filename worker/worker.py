import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, redis_client
from app.models import Task
import time
import json

QUEUE_NAME = "task_queue"
DEAD_LETTER_QUEUE = "dead_letter_queue"
WS_CHANNEL = "task_updates"
MAX_RETRIES = 3

def publish_update(task_id: str, status: str, retry_count: int = 0):
    """Publish task status update to Redis channel for WebSocket broadcast"""
    message = json.dumps({
        "type": "task_update",
        "task_id": task_id,
        "status": status,
        "retry_count": retry_count
    })
    redis_client.publish(WS_CHANNEL, message)

def process_task(payload: str) -> str:
    if "fail" in payload.lower():
        raise Exception(f"Simulated failure for payload: {payload}")
    time.sleep(2)
    return f"Processed: {payload}"

def run_worker():
    worker_id = os.getpid()
    print(f"[Worker {worker_id}] Started. Waiting for tasks...")

    while True:
        task_data = redis_client.brpop(QUEUE_NAME, timeout=5)

        if task_data is None:
            print(f"[Worker {worker_id}] No tasks. Waiting...")
            continue

        _, task_id = task_data
        print(f"[Worker {worker_id}] Picked up task: {task_id}")

        db = SessionLocal()
        task = None

        try:
            task = db.query(Task).filter(Task.id == task_id).first()

            if not task:
                print(f"[Worker {worker_id}] Task {task_id} not found. Skipping.")
                continue

            task.status = "processing"
            db.commit()
            publish_update(task_id, "processing", task.retry_count)
            print(f"[Worker {worker_id}] Task {task_id} → processing")

            result = process_task(task.payload)

            task.status = "done"
            task.result = result
            db.commit()
            publish_update(task_id, "done", task.retry_count)
            print(f"[Worker {worker_id}] Task {task_id} → done ✓")

        except Exception as e:
            print(f"[Worker {worker_id}] Task {task_id} FAILED: {e}")

            if task:
                task.retry_count += 1
                db.commit()

                if task.retry_count < MAX_RETRIES:
                    wait_time = 2 ** task.retry_count
                    print(f"[Worker {worker_id}] Retry {task.retry_count}/{MAX_RETRIES} in {wait_time}s...")
                    publish_update(task_id, f"retry_{task.retry_count}", task.retry_count)
                    time.sleep(wait_time)

                    task.status = "pending"
                    db.commit()
                    redis_client.rpush(QUEUE_NAME, str(task.id))

                else:
                    task.status = "failed"
                    task.result = f"Failed after {MAX_RETRIES} retries. Last error: {str(e)}"
                    db.commit()
                    publish_update(task_id, "failed", task.retry_count)
                    redis_client.rpush(DEAD_LETTER_QUEUE, str(task.id))
                    print(f"[Worker {worker_id}] Task {task_id} → DEAD LETTER QUEUE")

        finally:
            db.close()

if __name__ == "__main__":
    run_worker()