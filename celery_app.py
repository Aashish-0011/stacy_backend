from celery import Celery

#  celery app
celery_app = Celery("comfy_worker", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1", include=["tasks"])

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)