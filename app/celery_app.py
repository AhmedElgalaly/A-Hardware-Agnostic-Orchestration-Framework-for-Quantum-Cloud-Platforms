from __future__ import annotations

from celery import Celery

from app.config import settings

# Single Celery application shared by the API (producer) and the worker
# (consumer). For a local run without Redis/RabbitMQ, set
# CELERY_TASK_ALWAYS_EAGER=true so tasks execute synchronously in-process and
# no broker is required.
celery_app = Celery(
    "quantum_orchestrator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_always_eager,
    worker_max_tasks_per_child=100,
    broker_connection_retry_on_startup=True,
    # Prefetch one task at a time so a slow job does not hoard the queue ahead of
    # others. We intentionally do NOT enable acks_late/reject_on_worker_lost:
    # auto-requeuing a lost task could silently resubmit a billable real-hardware
    # job. Instead, a job orphaned by a worker restart is marked failed at startup
    # (see Orchestrator.recover_orphaned_jobs) and the user resubmits deliberately.
    worker_prefetch_multiplier=1,
)


from celery.signals import worker_process_init


@worker_process_init.connect
def _start_worker_metrics(**_kwargs) -> None:
    """Expose the worker's Prometheus metrics so Prometheus can scrape it.

    Run the worker with concurrency 1 (e.g. --pool=solo) so the executing
    process is the one exporting metrics. Binding is best-effort.
    """
    try:
        from app.observability import start_worker_metrics_server

        start_worker_metrics_server(settings.worker_metrics_port)
    except Exception:
        pass
