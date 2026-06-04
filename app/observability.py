from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Custom metrics live on the default Prometheus registry, so they are exposed
# both by the API's /metrics endpoint (via the FastAPI instrumentator) and by
# the Celery worker's metrics HTTP server. This gives end-to-end visibility of
# job orchestration regardless of which process executed the job.

PROVIDER_AVAILABLE = Gauge(
    "qaas_provider_available",
    "Provider availability: 1 if the provider is available, 0 otherwise.",
    ["provider"],
)


def set_provider_available(provider: str, available: bool) -> None:
    PROVIDER_AVAILABLE.labels(provider=provider).set(1 if available else 0)


JOBS_SUBMITTED = Counter(
    "qaas_jobs_submitted_total",
    "Total quantum jobs submitted.",
    ["strategy"],
)

JOBS_FINISHED = Counter(
    "qaas_jobs_finished_total",
    "Total quantum jobs that reached a terminal state.",
    ["strategy", "status"],
)

BACKEND_RUNS = Counter(
    "qaas_backend_runs_total",
    "Total per-backend executions.",
    ["provider", "backend", "status"],
)

BACKEND_EXECUTION_SECONDS = Histogram(
    "qaas_backend_execution_seconds",
    "Per-backend execution time in seconds.",
    ["provider", "backend"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)


def record_submitted(strategy: str) -> None:
    JOBS_SUBMITTED.labels(strategy=strategy).inc()


def record_finished(strategy: str, status: str) -> None:
    JOBS_FINISHED.labels(strategy=strategy, status=status).inc()


def record_backend_run(provider: str, backend: str, status: str, execution_time_ms: float | None) -> None:
    BACKEND_RUNS.labels(provider=provider, backend=backend, status=status).inc()
    if execution_time_ms is not None:
        BACKEND_EXECUTION_SECONDS.labels(provider=provider, backend=backend).observe(execution_time_ms / 1000.0)


def start_worker_metrics_server(port: int) -> None:
    """Expose the default registry over HTTP from the Celery worker process."""
    from prometheus_client import start_http_server

    start_http_server(port)
