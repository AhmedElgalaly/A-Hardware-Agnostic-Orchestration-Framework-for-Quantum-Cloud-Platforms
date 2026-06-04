from __future__ import annotations

from time import perf_counter

from qiskit import transpile

from app.adapters.base import QuantumBackendAdapter
from app.config import settings
from app.models import BackendCapability, BackendType, JobCreateRequest, NormalizedBackendResult
from app.services.circuit_translator import TranslatedCircuit
from app.services.result_normalizer import normalize_failure, normalize_success


class IBMQuantumAdapter(QuantumBackendAdapter):
    """Optional IBM Quantum adapter.

    The app remains fully functional without qiskit-ibm-runtime or IBM
    credentials. Set ENABLE_IBM=true and IBM_QUANTUM_TOKEN to enable discovery.
    """

    _provider = "ibm"
    _CACHE_TTL_SECONDS = 300

    def __init__(self) -> None:
        self._service = None
        self._import_error: str | None = None
        self._auth_error: str | None = None
        self._caps_cache: list[BackendCapability] | None = None
        self._caps_cached_at: float = 0.0
        self._initialize_service()

    def provider_name(self) -> str:
        return self._provider

    def is_available(self) -> bool:
        return self._service is not None

    def capabilities(self) -> list[BackendCapability]:
        if not self._service:
            return []
        from time import time

        now = time()
        if self._caps_cache is not None and (now - self._caps_cached_at) < self._CACHE_TTL_SECONDS:
            return self._caps_cache
        self._caps_cache = self._discover_capabilities()
        self._caps_cached_at = now
        return self._caps_cache

    def _discover_capabilities(self) -> list[BackendCapability]:
        capabilities: list[BackendCapability] = []
        try:
            for backend in self._service.backends():
                config = backend.configuration()
                status = backend.status()
                backend_name = self._backend_name(backend)
                backend_type = BackendType.simulator if getattr(config, "simulator", False) else BackendType.hardware
                capabilities.append(
                    BackendCapability(
                        provider=self._provider,
                        backend_name=backend_name,
                        backend_type=backend_type,
                        num_qubits=getattr(config, "n_qubits", 0),
                        native_gates=list(getattr(config, "basis_gates", []) or []),
                        topology="ibm_coupling_map",
                        noise_model_available=backend_type == BackendType.simulator,
                        estimated_latency_ms=5000 + (getattr(status, "pending_jobs", 0) * 1000),
                        queue_time_ms=float(getattr(status, "pending_jobs", 0) * 1000),
                        coupling_map=getattr(config, "coupling_map", None),
                        metadata={"pending_jobs": getattr(status, "pending_jobs", None)},
                    )
                )
        except Exception:
            return []
        return capabilities

    def supports_backend(self, backend_name: str) -> bool:
        return any(backend.backend_name == backend_name for backend in self.capabilities())

    def run(
        self,
        job_id: str,
        circuit: TranslatedCircuit,
        job_request: JobCreateRequest,
        backend_capability: BackendCapability,
    ) -> NormalizedBackendResult:
        if not self._service:
            return normalize_failure(
                backend_capability,
                job_request.shots,
                self._auth_error or self._import_error or "IBM credentials not configured.",
                circuit.internal.metadata,
            )

        try:
            backend = self._service.backend(backend_capability.backend_name)
            depth_before = circuit.qiskit.depth() or 0
            started = perf_counter()

            # Modern IBM Runtime requires ISA circuits + the SamplerV2 primitive.
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
            from qiskit_ibm_runtime import SamplerV2

            pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
            isa_circuit = pass_manager.run(circuit.qiskit)

            sampler = SamplerV2(mode=backend)
            job = sampler.run([isa_circuit], shots=job_request.shots)
            result = job.result()
            execution_time_ms = round((perf_counter() - started) * 1000, 3)

            counts = _extract_counts(result[0], circuit.qiskit)
            return normalize_success(
                backend_capability,
                job_request.shots,
                counts,
                circuit.internal.metadata,
                execution_time_ms,
                depth_before,
                isa_circuit.depth() or 0,
            )
        except Exception as exc:
            return normalize_failure(backend_capability, job_request.shots, str(exc), circuit.internal.metadata)

    def _initialize_service(self) -> None:
        if not settings.enable_ibm:
            self._auth_error = "IBM adapter is disabled. Set ENABLE_IBM=true to enable it."
            return

        token = settings.ibm_quantum_token
        if not token:
            self._auth_error = "IBM credentials not configured. Set IBM_QUANTUM_TOKEN."
            return
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
        except Exception as exc:
            self._import_error = f"qiskit-ibm-runtime is not installed: {exc}"
            return
        try:
            kwargs = {"channel": settings.ibm_channel, "token": token}
            if settings.ibm_instance:
                kwargs["instance"] = settings.ibm_instance
            self._service = QiskitRuntimeService(**kwargs)
        except Exception as exc:
            self._auth_error = f"IBM authentication failed: {type(exc).__name__}"
            self._service = None

    def _backend_name(self, backend) -> str:
        name = getattr(backend, "name", None)
        return str(name() if callable(name) else name)


def _extract_counts(pub_result, qiskit_circuit) -> dict[str, int]:
    """Pull measurement counts out of a SamplerV2 PubResult.

    The classical register name is used to locate the BitArray; falls back to
    the first available data field for robustness across qiskit versions.
    """
    data = pub_result.data
    creg_name = qiskit_circuit.cregs[0].name if qiskit_circuit.cregs else "meas"
    bit_array = getattr(data, creg_name, None)
    if bit_array is None:
        try:
            bit_array = next(iter(data.values()))
        except Exception:
            bit_array = None
    if bit_array is None:
        return {}
    return {str(state): int(count) for state, count in bit_array.get_counts().items()}
