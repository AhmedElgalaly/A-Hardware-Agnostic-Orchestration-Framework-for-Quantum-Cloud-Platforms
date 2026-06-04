export type CircuitFormat = "openqasm2" | "json";
export type ExecutionStrategy = "fastest" | "benchmark_all";
export type BackendType = "any" | "simulator" | "hardware";
export type BackendRunStatus = "completed" | "failed" | "skipped";
export type JobStatus = "pending" | "running" | "completed" | "failed" | "partial";

export interface JsonGate {
  name: string;
  targets: number[];
  controls?: number[];
  params?: number[];
}

export interface CircuitSpec {
  format: CircuitFormat;
  source?: string;
  qubits?: number;
  classical_bits?: number;
  gates?: JsonGate[];
}

export interface ExecutionOptions {
  strategy: ExecutionStrategy;
  backend_type: BackendType;
  provider: "auto" | "qiskit" | "ibm" | "aws" | "azure" | string;
  objective: "min_latency" | "max_fidelity" | "min_cost" | "compare" | string;
  min_qubits?: number;
}

export interface JobRequest {
  name?: string;
  circuit: CircuitSpec;
  shots: number;
  execution: ExecutionOptions;
}

export interface BackendCapability {
  provider: string;
  backend_name: string;
  backend_type: "simulator" | "hardware";
  num_qubits: number;
  native_gates: string[];
  topology: string;
  noise_model_available: boolean;
  estimated_latency_ms: number;
  queue_time_ms?: number | null;
  fidelity?: number | null;
  coupling_map?: number[][] | null;
  metadata: Record<string, unknown>;
}

export interface JobCreateResponse {
  job_id: string;
  name?: string | null;
  status: JobStatus;
  result_url: string;
}

export interface JobSummary {
  job_id: string;
  name?: string | null;
  strategy: ExecutionStrategy;
  status: JobStatus;
  created_at: string;
  updated_at: string;
}

export interface BackendRunMetrics {
  execution_time_ms?: number | null;
  depth_before_transpile?: number | null;
  depth_after_transpile?: number | null;
  num_qubits?: number | null;
  operation_count?: number | null;
  selected_backend?: string | null;
  provider?: string | null;
  status?: BackendRunStatus | null;
  timestamp?: string | null;
}

export interface NormalizedBackendResult {
  provider: string;
  backend: string;
  backend_type: "simulator" | "hardware";
  status: BackendRunStatus;
  shots: number;
  counts: Record<string, number>;
  metrics: BackendRunMetrics;
  error?: string | null;
}

export interface NormalizedJobResult {
  job_id: string;
  name?: string | null;
  strategy: ExecutionStrategy;
  status: JobStatus;
  results: NormalizedBackendResult[];
  errors: string[];
  created_at: string;
  updated_at: string;
}
