from __future__ import annotations

from time import perf_counter

from qiskit import transpile
from qiskit_aer import AerSimulator

from app.adapters.base import QuantumBackendAdapter
from app.models import BackendCapability, BackendType, JobCreateRequest, NormalizedBackendResult
from app.services.circuit_translator import TranslatedCircuit
from app.services.result_normalizer import normalize_failure, normalize_success


class QiskitAerAdapter(QuantumBackendAdapter):
    _provider = "qiskit"
    _backend_name = "aer_simulator"

    def __init__(self) -> None:
        self._backend = AerSimulator()

    def provider_name(self) -> str:
        return self._provider

    def is_available(self) -> bool:
        return True

    def capabilities(self) -> list[BackendCapability]:
        return [
            BackendCapability(
                provider=self._provider,
                backend_name=self._backend_name,
                backend_type=BackendType.simulator,
                num_qubits=32,
                native_gates=["h", "x", "y", "z", "rx", "ry", "rz", "cx", "cz", "measure"],
                topology="fully_connected_simulated",
                noise_model_available=False,
                estimated_latency_ms=50,
                coupling_map=None,
                metadata={"sdk": "qiskit-aer", "local": True},
            )
        ]

    def supports_backend(self, backend_name: str) -> bool:
        return backend_name == self._backend_name

    def run(
        self,
        job_id: str,
        circuit: TranslatedCircuit,
        job_request: JobCreateRequest,
        backend_capability: BackendCapability,
    ) -> NormalizedBackendResult:
        if not self.supports_backend(backend_capability.backend_name):
            return normalize_failure(
                backend_capability,
                job_request.shots,
                f"Qiskit Aer adapter does not support backend '{backend_capability.backend_name}'.",
                circuit.internal.metadata,
            )

        try:
            qiskit_circuit = circuit.qiskit
            depth_before = qiskit_circuit.depth() or 0
            started = perf_counter()
            transpiled = transpile(qiskit_circuit, self._backend)
            aer_result = self._backend.run(transpiled, shots=job_request.shots).result()
            execution_time_ms = round((perf_counter() - started) * 1000, 3)
            counts = aer_result.get_counts()
            return normalize_success(
                backend=backend_capability,
                shots=job_request.shots,
                counts=counts,
                metadata=circuit.internal.metadata,
                execution_time_ms=execution_time_ms,
                depth_before_transpile=depth_before,
                depth_after_transpile=transpiled.depth() or 0,
            )
        except Exception as exc:
            return normalize_failure(backend_capability, job_request.shots, str(exc), circuit.internal.metadata)
