from __future__ import annotations

from uuid import uuid4

from app.adapters import AWSBraketAdapter, AzureQuantumAdapter, IBMQuantumAdapter, QiskitAerAdapter
from app.adapters.base import QuantumBackendAdapter
from app.models import (
    BackendCapability,
    BackendRunMetrics,
    BackendRunStatus,
    JobCreateRequest,
    JobCreateResponse,
    JobResultResponse,
    JobStatus,
    NormalizedBackendResult,
)
from app.parser import translate_circuit
from app.repository import JobRepository
from app.selection import select_backends
from app.services.result_normalizer import normalize_failure, utc_now_iso
from app import observability


class JobNotFoundError(KeyError):
    pass


class OrchestrationError(RuntimeError):
    pass


class Orchestrator:
    """Coordinates parsing, backend selection, execution, normalization, and persistence.

    Jobs run synchronously for the prototype, but the repository-backed state
    transitions keep the design ready for background execution later.
    """

    def __init__(
        self,
        adapters: list[QuantumBackendAdapter] | None = None,
        repository: JobRepository | None = None,
    ) -> None:
        self.adapters = adapters or [
            QiskitAerAdapter(),
            IBMQuantumAdapter(),
            AWSBraketAdapter(),
            AzureQuantumAdapter(),
        ]
        self.repository = repository or JobRepository()
        self._log_provider_status()

    def list_backends(self) -> list[BackendCapability]:
        backends: list[BackendCapability] = []
        for adapter in self.adapters:
            if adapter.is_available():
                backends.extend(adapter.capabilities())
        return backends

    def provider_status(self) -> list[dict]:
        """Report each provider's availability and, if unavailable, the reason.

        This surfaces why a provider (e.g. AWS Braket) is not in /backends:
        disabled, SDK not installed, missing config, or auth failure.
        """
        statuses: list[dict] = []
        for adapter in self.adapters:
            available = adapter.is_available()
            reason = (
                getattr(adapter, "_auth_error", None)
                or getattr(adapter, "_import_error", None)
            )
            observability.set_provider_available(adapter.provider_name(), available)
            statuses.append(
                {
                    "provider": adapter.provider_name(),
                    "available": available,
                    "reason": None if available else (reason or "unavailable"),
                }
            )
        return statuses

    def _log_provider_status(self) -> None:
        import logging

        logger = logging.getLogger("quantum_orchestrator")
        for status in self.provider_status():
            if status["available"]:
                logger.info("Provider '%s' is available.", status["provider"])
            else:
                logger.warning(
                    "Provider '%s' is NOT available: %s", status["provider"], status["reason"]
                )

    def list_jobs(self):
        return self.repository.list()

    def submit_job(self, request: JobCreateRequest) -> JobResultResponse:
        job_id = str(uuid4())
        self.repository.create(
            job_id=job_id,
            name=request.name,
            request_body=request.model_dump(mode="json"),
            strategy=request.execution.strategy.value,
        )
        observability.record_submitted(request.execution.strategy.value)
        # Dispatch to a Celery worker. With CELERY_TASK_ALWAYS_EAGER=true this
        # runs inline (local, no broker) and the job is already finished when we
        # read it back. In async mode it returns immediately as "pending" and the
        # worker drives the pending -> running -> completed/partial/failed flow.
        self.repository.update(job_id, JobStatus.pending)

        from app.config import settings

        if settings.celery_task_always_eager:
            # Local, no-broker mode: execute in-process using this orchestrator's
            # configured adapters (keeps dependency injection intact).
            return self.run_job(job_id, request)

        # Async mode: hand off to a Celery worker and return immediately. The
        # client polls GET /jobs/{id} for the pending -> running -> done flow.
        from app.tasks import execute_job_task

        execute_job_task.delay(job_id, request.model_dump(mode="json"))
        return self.get_job(job_id)

    def run_job(self, job_id: str, request: JobCreateRequest) -> JobResultResponse:
        """Execute an already-persisted job. Called by the Celery worker."""
        return self._execute_existing_job(job_id, request)

    def rerun_job(self, job_id: str) -> JobCreateResponse:
        stored = self._get_stored(job_id)
        request = JobCreateRequest.model_validate(stored.request)
        rerun = self.submit_job(request)
        return JobCreateResponse(
            job_id=rerun.job_id,
            name=rerun.name,
            status=rerun.status,
            result_url=f"/jobs/{rerun.job_id}/result",
        )

    def get_job(self, job_id: str) -> JobResultResponse:
        stored = self._get_stored(job_id)
        return JobResultResponse(
            job_id=stored.job_id,
            name=stored.name,
            strategy=stored.strategy,
            status=stored.status,
            results=stored.results,
            errors=stored.errors,
            created_at=stored.created_at,
            updated_at=stored.updated_at,
        )

    def get_result(self, job_id: str) -> JobResultResponse:
        return self.get_job(job_id)

    def _execute_existing_job(self, job_id: str, request: JobCreateRequest) -> JobResultResponse:
        try:
            self.repository.update(job_id, JobStatus.running)
            translated = translate_circuit(request.circuit)
            selected_backends = select_backends(request.execution, translated.internal, self.adapters)

            # Seed one result entry per selected backend with status "pending" so
            # the UI can list every backend the job will run on, together with its
            # state, before any of them has executed.
            results = [self._backend_placeholder(b, request.shots, BackendRunStatus.pending) for b in selected_backends]
            self._persist(job_id, JobStatus.running, selected_backends, results, [])

            errors: list[str] = []
            for index, backend in enumerate(selected_backends):
                # Mark this backend "running" and persist before execution, so the
                # state is visible while a (possibly slow) backend executes.
                results[index] = self._backend_placeholder(backend, request.shots, BackendRunStatus.running)
                self._persist(job_id, JobStatus.running, selected_backends, results, errors)
                try:
                    adapter = self._adapter_for_backend(backend)
                    result = adapter.run(job_id, translated, request, backend)
                except Exception as exc:
                    # benchmark_all must be resilient: one provider failure should
                    # become a per-backend failed result, not erase successful runs.
                    result = normalize_failure(
                        backend=backend,
                        shots=request.shots,
                        error=str(exc),
                        metadata=translated.internal.metadata,
                    )
                results[index] = result
                observability.record_backend_run(
                    provider=result.provider,
                    backend=result.backend,
                    status=result.status.value,
                    execution_time_ms=result.metrics.execution_time_ms,
                )
                if result.error:
                    errors.append(f"{backend.provider}/{backend.backend_name}: {result.error}")
                # Persist after each backend completes so progress survives even
                # if the worker is restarted mid-job.
                self._persist(job_id, JobStatus.running, selected_backends, results, errors)

            status = self._job_status_for_results(results)
            observability.record_finished(request.execution.strategy.value, status.value)
            stored = self._persist(job_id, status, selected_backends, results, errors)
            return self.get_job(stored.job_id)
        except Exception as exc:
            observability.record_finished(request.execution.strategy.value, JobStatus.failed.value)
            self.repository.update(job_id, JobStatus.failed, errors=[str(exc)])
            raise

    def _persist(self, job_id, status, selected_backends, results, errors):
        return self.repository.update(
            job_id,
            status,
            selected_backends=[b.model_dump(mode="json") for b in selected_backends],
            results=[r.model_dump(mode="json") for r in results],
            errors=errors,
        )

    def _backend_placeholder(self, backend: BackendCapability, shots: int, status: BackendRunStatus) -> NormalizedBackendResult:
        return NormalizedBackendResult(
            provider=backend.provider,
            backend=backend.backend_name,
            backend_type=backend.backend_type,
            status=status,
            shots=shots,
            counts={},
            metrics=BackendRunMetrics(
                selected_backend=backend.backend_name,
                provider=backend.provider,
                status=status,
                timestamp=utc_now_iso(),
            ),
            error=None,
        )

    def recover_orphaned_jobs(self) -> int:
        """Fail jobs left pending/running past the staleness threshold.

        These are jobs whose worker restarted before they reached a terminal
        state; without this they would appear stuck forever in the UI.
        """
        import logging

        from app.config import settings

        recovered = self.repository.fail_stale(settings.stale_job_minutes)
        if recovered:
            logging.getLogger("quantum_orchestrator").warning(
                "Recovered %d orphaned job(s) older than %d minutes (marked failed).",
                recovered,
                settings.stale_job_minutes,
            )
        return recovered

    def _adapter_for_backend(self, backend: BackendCapability) -> QuantumBackendAdapter:
        for adapter in self.adapters:
            if adapter.provider_name() == backend.provider and adapter.supports_backend(backend.backend_name):
                return adapter
        raise OrchestrationError(f"No adapter found for backend '{backend.provider}/{backend.backend_name}'.")

    def _get_stored(self, job_id: str):
        try:
            return self.repository.get(job_id)
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc

    def _job_status_for_results(self, results) -> JobStatus:
        if not results:
            return JobStatus.failed
        completed = [result for result in results if result.status == BackendRunStatus.completed]
        failed = [result for result in results if result.status == BackendRunStatus.failed]
        if completed and failed:
            return JobStatus.partial
        if completed:
            return JobStatus.completed
        return JobStatus.failed
