import os
from celery import Celery

# Use Redis as broker and backend
# Fallback to localhost if not specified (for local dev)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "bod_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
