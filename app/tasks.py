from __future__ import annotations

from app.celery_app import celery_app
from app.models import JobCreateRequest


@celery_app.task(name="app.tasks.execute_job_task", bind=True, max_retries=0)
def execute_job_task(self, job_id: str, request_body: dict) -> dict:
    """Background execution of a quantum job.

    The orchestrator is constructed inside the task so each worker process owns
    its own adapter instances and database connections. The request is passed as
    a plain dict (JSON-serializable) and revalidated here.
    """
    # Imported lazily to avoid a circular import at module load time.
    from app.orchestrator import Orchestrator

    request = JobCreateRequest.model_validate(request_body)
    orchestrator = Orchestrator()
    result = orchestrator.run_job(job_id, request)
    return result.model_dump(mode="json")
