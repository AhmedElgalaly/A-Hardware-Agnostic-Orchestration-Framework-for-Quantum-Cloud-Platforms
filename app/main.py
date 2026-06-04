from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import BackendCapability, JobCreateRequest, JobCreateResponse, JobResultResponse, JobSummary
from app.orchestrator import JobNotFoundError, OrchestrationError, Orchestrator
from app.parser import CircuitParseError
from app.selection import BackendSelectionError

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Submit quantum circuits once, discover compatible backends, execute on "
        "the fastest backend or benchmark all compatible backends, and retrieve "
        "normalized metrics from persisted jobs."
    ),
)
orchestrator = Orchestrator()
# Clean up jobs left pending/running by a previous, now-restarted worker so the
# UI never shows jobs stuck forever.
orchestrator.recover_orphaned_jobs()

# Expose Prometheus metrics at /metrics (HTTP metrics + custom qaas_* metrics
# from app.observability, which share the default registry).
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["system"])
except Exception:  # pragma: no cover - metrics are non-critical to the API
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed. Check circuit format, execution strategy, shots, and field names.",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(CircuitParseError)
async def circuit_parse_error_handler(_: Request, exc: CircuitParseError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


@app.exception_handler(BackendSelectionError)
async def backend_selection_error_handler(_: Request, exc: BackendSelectionError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(OrchestrationError)
async def orchestration_error_handler(_: Request, exc: OrchestrationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/backends", response_model=list[BackendCapability], tags=["backends"])
def get_backends() -> list[BackendCapability]:
    return orchestrator.list_backends()


@app.get("/providers", tags=["backends"])
def get_providers() -> list[dict]:
    """Diagnostics: each provider's availability and, if down, the reason
    (disabled, SDK not installed, missing config, or auth failure)."""
    return orchestrator.provider_status()


@app.post("/jobs", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED, tags=["jobs"])
def create_job(request: JobCreateRequest) -> JobCreateResponse:
    job = orchestrator.submit_job(request)
    return JobCreateResponse(
        job_id=job.job_id,
        name=job.name,
        status=job.status,
        result_url=f"/jobs/{job.job_id}/result",
    )


@app.get("/jobs", response_model=list[JobSummary], tags=["jobs"])
def list_jobs() -> list[JobSummary]:
    return orchestrator.list_jobs()


@app.get("/jobs/{job_id}", response_model=JobResultResponse, tags=["jobs"])
def get_job(job_id: str) -> JobResultResponse:
    try:
        return orchestrator.get_job(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.") from exc


@app.get("/jobs/{job_id}/result", response_model=JobResultResponse, tags=["jobs"])
def get_job_result(job_id: str) -> JobResultResponse:
    try:
        return orchestrator.get_result(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.") from exc


@app.post("/jobs/{job_id}/rerun", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED, tags=["jobs"])
def rerun_job(job_id: str) -> JobCreateResponse:
    try:
        return orchestrator.rerun_job(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.") from exc
