import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.database import SessionLocal, redis_client
from app.models import Task 
import time

def process_task(payload: str) -> str:
    # Simulate work
    time.sleep(2)
    return f"Processed: {payload}"

def run_worker():
    print("Worker started, waiting for tasks...")
    while True:
        task_data = redis_client.brpop("task_queue", timeout=5)
        if task_data is None:
            continue

        _, task_id = task_data
        print(f"Picked up task: {task_id}")

        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                continue

            task.status = "processing"
            db.commit()

            result = process_task(task.payload)

            task.status = "done"
            task.result = result
            db.commit()
            print(f"Task {task_id} completed!")

        except Exception as e:
            task.status = "failed"
            task.result = str(e)
            db.commit()
            print(f"Task {task_id} failed: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    run_worker()