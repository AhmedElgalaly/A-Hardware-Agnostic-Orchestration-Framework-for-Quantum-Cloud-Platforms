# Implementation Notes (for the report's Implementation chapter)

This document maps the delivered system to the architecture proposed in the
interim report and records the deliberate local-first design decisions.

## Design decision: local-first, no authentication

The platform is a single-researcher tool that runs on one machine. The report's
JWT authentication and API-key management requirements were intentionally
dropped: there is no login and no user management. This keeps the tool simple to
run and matches its purpose — reducing friction for a researcher comparing
quantum backends, not operating a multi-tenant cloud service. Provider
credentials are read from a local `.env` file, are never returned by any API
response, and are never written to the database.

## Architecture as built

| Report component | Delivered implementation |
| --- | --- |
| API Gateway (FastAPI) | `app/main.py` — REST endpoints for jobs, backends, health, and `/metrics`. |
| Message broker (RabbitMQ) | Redis (`redis:7-alpine`) as the Celery broker + result backend. Redis was chosen over RabbitMQ for a lighter local footprint; the broker is a configurable URL, so RabbitMQ can be swapped in without code changes. |
| Worker nodes (Celery) | `app/celery_app.py` + `app/tasks.py`. `execute_job_task` runs the full orchestration in a worker process. A synchronous *eager* mode (`CELERY_TASK_ALWAYS_EAGER=true`) runs jobs in-process for quick local use. |
| Provider adapters | `app/adapters/` — Qiskit Aer (local), IBM Quantum (SamplerV2 primitives), AWS Braket (`amazon-braket-sdk`), Azure Quantum (`azure-quantum` Qiskit provider). All share the `QuantumBackendAdapter` interface. |
| Scheduling / backend selection | `app/selection.py` — filters by qubits, type, provider, and native gate set; `fastest` picks lowest estimated latency + queue time, `benchmark_all` runs every compatible backend. |
| Fallback / resilience | `benchmark_all` tolerates per-backend failures (a provider error becomes a per-backend failed result, not a whole-job failure). Disabled/uncredentialed adapters report themselves unavailable and are skipped. |
| Storage (PostgreSQL + MinIO) | SQLite (WAL mode for concurrent API + worker access) for job metadata and results; local filesystem (`RESULTS_DIR`) replaces MinIO/S3 for the local deployment. |
| Monitoring (Prometheus + Grafana) | `app/observability.py` exposes `qaas_*` counters/histograms; `/metrics` on the API and a `:9100` exporter on the worker; `monitoring/` provides the Prometheus scrape config and an auto-provisioned Grafana dashboard. |
| SDKs (Python/JS) | Not implemented — out of scope for the local tool; the REST API + OpenAPI docs serve as the interface. (Listed as possible future work.) |
| Developer tools (QRNG, optimizers) | Not implemented in this iteration; the platform focuses on unified submission, selection, execution, normalization, and monitoring. |

## Result normalization

Every backend result is normalized to one schema regardless of provider:
provider, backend, backend type, status, shots, counts, metrics (execution time,
transpilation depth before/after, qubit/operation counts, timestamp), and an
optional error. This is what makes heterogeneous providers directly comparable.

## Job lifecycle

`pending → running → completed | partial | failed`. The API persists the job as
`pending`, dispatches to the worker (or runs eagerly), and the worker drives the
remaining transitions. Clients poll `GET /jobs/{id}`.

## Testing

`pytest` runs fully offline (no broker, no credentials) via `tests/conftest.py`,
which forces eager execution. The suite covers parsing, selection, Aer
execution, the async/eager submission path, the `/metrics` endpoint, and the
graceful "unavailable" behavior of the IBM/AWS/Azure adapters.

## What still requires the user (credentialed, untestable here)

Real-hardware execution on IBM, AWS Braket, and Azure Quantum requires valid
credentials and the optional provider SDKs. The adapter code is complete, but
end-to-end execution against live devices must be verified by the user with
their own accounts. IBM Quantum's free tier is the recommended path for a
real-hardware demonstration.
