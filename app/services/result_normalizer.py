from __future__ import annotations

from datetime import datetime, timezone

from app.models import (
    BackendCapability,
    BackendRunMetrics,
    BackendRunStatus,
    CircuitMetadata,
    NormalizedBackendResult,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_success(
    backend: BackendCapability,
    shots: int,
    counts: dict[str, int],
    metadata: CircuitMetadata,
    execution_time_ms: float,
    depth_before_transpile: int,
    depth_after_transpile: int,
) -> NormalizedBackendResult:
    return NormalizedBackendResult(
        provider=backend.provider,
        backend=backend.backend_name,
        backend_type=backend.backend_type,
        status=BackendRunStatus.completed,
        shots=shots,
        counts={str(key): int(value) for key, value in sorted(counts.items())},
        metrics=BackendRunMetrics(
            execution_time_ms=execution_time_ms,
            depth_before_transpile=depth_before_transpile,
            depth_after_transpile=depth_after_transpile,
            num_qubits=metadata.num_qubits,
            operation_count=metadata.operation_count,
            selected_backend=backend.backend_name,
            provider=backend.provider,
            status=BackendRunStatus.completed,
            timestamp=utc_now_iso(),
        ),
        error=None,
    )


def normalize_failure(
    backend: BackendCapability,
    shots: int,
    error: str,
    metadata: CircuitMetadata | None = None,
) -> NormalizedBackendResult:
    return NormalizedBackendResult(
        provider=backend.provider,
        backend=backend.backend_name,
        backend_type=backend.backend_type,
        status=BackendRunStatus.failed,
        shots=shots,
        counts={},
        metrics=BackendRunMetrics(
            num_qubits=metadata.num_qubits if metadata else None,
            operation_count=metadata.operation_count if metadata else None,
            selected_backend=backend.backend_name,
            provider=backend.provider,
            status=BackendRunStatus.failed,
            timestamp=utc_now_iso(),
        ),
        error=error,
    )
