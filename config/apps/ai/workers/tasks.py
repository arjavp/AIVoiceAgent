from celery import shared_task
import time

@shared_task
def generic_background_task(data):
    """
    Simulates a long-running Tool Calling operation (e.g., saving to a DB, calling Salesforce).
    This runs asynchronously in Redis, freeing up the WebSocket instantly.
    """
    print(f"Worker received: {data}")
    time.sleep(5)  # Simulate 5-second API Call
    print("Worker finished processing ticket.")
    return True