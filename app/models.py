from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CircuitFormat(str, Enum):
    openqasm2 = "openqasm2"
    json = "json"


class ExecutionStrategy(str, Enum):
    fastest = "fastest"
    benchmark_all = "benchmark_all"


class BackendType(str, Enum):
    any = "any"
    simulator = "simulator"
    hardware = "hardware"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class BackendRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class CircuitSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    format: CircuitFormat
    source: str | None = None
    qubits: int | None = None
    classical_bits: int | None = None
    gates: list[dict[str, Any]] | None = None

    @model_validator(mode="after")
    def validate_by_format(self) -> "CircuitSpec":
        if self.format == CircuitFormat.openqasm2 and not isinstance(self.source, str):
            raise ValueError("OpenQASM 2 circuits require a string 'source'.")
        if self.format == CircuitFormat.json:
            if not isinstance(self.qubits, int) or self.qubits <= 0:
                raise ValueError("JSON circuits require a positive integer 'qubits'.")
            if self.gates is None:
                raise ValueError("JSON circuits require a 'gates' list.")
        return self


class ExecutionOptions(BaseModel):
    strategy: ExecutionStrategy = ExecutionStrategy.fastest
    backend_type: BackendType = BackendType.any
    provider: str = "auto"
    objective: str = "min_latency"
    min_qubits: int | None = None


class JobCreateRequest(BaseModel):
    name: str | None = None
    circuit: CircuitSpec
    shots: int = Field(default=1024, ge=1, le=100_000)
    execution: ExecutionOptions = Field(default_factory=ExecutionOptions)


class JobCreateResponse(BaseModel):
    job_id: str
    name: str | None = None
    status: JobStatus
    result_url: str


class CircuitMetadata(BaseModel):
    num_qubits: int
    num_clbits: int
    gate_names: list[str] = Field(default_factory=list)
    operation_count: int
    has_measurements: bool


class InternalOperation(BaseModel):
    name: str
    targets: list[int] = Field(default_factory=list)
    controls: list[int] = Field(default_factory=list)
    params: list[float] = Field(default_factory=list)


class InternalCircuit(BaseModel):
    format: CircuitFormat
    num_qubits: int
    num_clbits: int
    operations: list[InternalOperation] = Field(default_factory=list)
    metadata: CircuitMetadata
    raw_source: str | dict[str, Any]


class BackendCapability(BaseModel):
    provider: str
    backend_name: str
    backend_type: BackendType
    num_qubits: int
    native_gates: list[str] = Field(default_factory=list)
    topology: str = "unknown"
    noise_model_available: bool = False
    estimated_latency_ms: float = 1000
    queue_time_ms: float | None = None
    fidelity: float | None = None
    coupling_map: list[list[int]] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BackendRunMetrics(BaseModel):
    execution_time_ms: float | None = None
    depth_before_transpile: int | None = None
    depth_after_transpile: int | None = None
    num_qubits: int | None = None
    operation_count: int | None = None
    selected_backend: str | None = None
    provider: str | None = None
    status: BackendRunStatus | None = None
    timestamp: str | None = None


class NormalizedBackendResult(BaseModel):
    provider: str
    backend: str
    backend_type: BackendType
    status: BackendRunStatus
    shots: int
    counts: dict[str, int] = Field(default_factory=dict)
    metrics: BackendRunMetrics = Field(default_factory=BackendRunMetrics)
    error: str | None = None


class JobResultResponse(BaseModel):
    job_id: str
    name: str | None = None
    strategy: ExecutionStrategy
    status: JobStatus
    results: list[NormalizedBackendResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class JobSummary(BaseModel):
    job_id: str
    name: str | None = None
    strategy: ExecutionStrategy
    status: JobStatus
    created_at: str
    updated_at: str


class StoredJob(BaseModel):
    job_id: str
    name: str | None = None
    request: dict[str, Any]
    strategy: ExecutionStrategy
    status: JobStatus
    selected_backends: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
