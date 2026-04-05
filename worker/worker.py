import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, redis_client
from app.models import Task
import time

QUEUE_NAME = "task_queue"
DEAD_LETTER_QUEUE = "dead_letter_queue"
MAX_RETRIES = 3

def process_task(payload: str) -> str:
    # Simulate a task that randomly fails
    # We'll force a failure if payload contains "fail"
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

            # Mark as processing
            task.status = "processing"
            db.commit()
            print(f"[Worker {worker_id}] Task {task_id} → processing")

            # Do the actual work (may raise Exception)
            result = process_task(task.payload)

            # Success!
            task.status = "done"
            task.result = result
            db.commit()
            print(f"[Worker {worker_id}] Task {task_id} → done ✓")

        except Exception as e:
            print(f"[Worker {worker_id}] Task {task_id} FAILED: {e}")

            if task:
                task.retry_count += 1
                db.commit()

                if task.retry_count < MAX_RETRIES:
                    # Calculate wait time: 2^retry_count seconds
                    # retry 1 = wait 2s, retry 2 = wait 4s, retry 3 = wait 8s
                    wait_time = 2 ** task.retry_count
                    print(f"[Worker {worker_id}] Retry {task.retry_count}/{MAX_RETRIES} in {wait_time}s...")
                    time.sleep(wait_time)

                    # Re-queue the task ID back into Redis
                    task.status = "pending"
                    db.commit()
                    redis_client.rpush(QUEUE_NAME, str(task.id))
                    print(f"[Worker {worker_id}] Task {task_id} re-queued for retry")

                else:
                    # Max retries exceeded → dead letter queue
                    task.status = "failed"
                    task.result = f"Failed after {MAX_RETRIES} retries. Last error: {str(e)}"
                    db.commit()

                    redis_client.rpush(DEAD_LETTER_QUEUE, str(task.id))
                    print(f"[Worker {worker_id}] Task {task_id} → DEAD LETTER QUEUE after {MAX_RETRIES} retries")

        finally:
            db.close()

if __name__ == "__main__":
    run_worker()