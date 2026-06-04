from __future__ import annotations

from app.adapters.base import QuantumBackendAdapter
from app.models import BackendCapability, BackendType, ExecutionOptions, ExecutionStrategy, InternalCircuit


class BackendSelectionError(ValueError):
    pass


# Standard gates the Qiskit transpiler can decompose into any universal native
# basis (which all supported real backends expose). A backend reporting only its
# native basis (e.g. IBM's ecr/rz/sx/x) does not list h/cx/measure, but it can
# still run them after transpilation, so these must not be filtered out.
_TRANSPILABLE_GATES = {
    "h", "x", "y", "z", "s", "sdg", "t", "tdg",
    "rx", "ry", "rz", "p", "u", "u1", "u2", "u3",
    "cx", "cz", "cy", "ch", "swap", "ccx",
    "id", "sx", "sxdg", "ecr",
    "measure", "barrier", "reset",
}


def discover_available_backends(adapters: list[QuantumBackendAdapter]) -> list[BackendCapability]:
    backends: list[BackendCapability] = []
    for adapter in adapters:
        if not adapter.is_available():
            continue
        backends.extend(adapter.capabilities())
    return backends


def select_backends(
    execution: ExecutionOptions,
    circuit: InternalCircuit,
    adapters: list[QuantumBackendAdapter],
) -> list[BackendCapability]:
    compatible = [
        backend
        for backend in discover_available_backends(adapters)
        if is_compatible(backend, execution, circuit)
    ]

    if not compatible:
        required_gates = sorted({gate for gate in circuit.metadata.gate_names if gate != "barrier"})
        raise BackendSelectionError(
            "No compatible backend found. "
            f"Required qubits: {execution.min_qubits or circuit.num_qubits}; "
            f"backend_type: {execution.backend_type}; provider: {execution.provider}; "
            f"required_gates: {required_gates}."
        )

    if execution.strategy == ExecutionStrategy.fastest:
        return [min(compatible, key=_latency_sort_key)]
    if execution.strategy == ExecutionStrategy.benchmark_all:
        return sorted(compatible, key=_latency_sort_key)

    raise BackendSelectionError(f"Unsupported execution strategy: {execution.strategy}")


def is_compatible(
    backend: BackendCapability,
    execution: ExecutionOptions,
    circuit: InternalCircuit,
) -> bool:
    min_qubits = execution.min_qubits or circuit.num_qubits
    if backend.num_qubits < min_qubits or backend.num_qubits < circuit.num_qubits:
        return False
    if execution.backend_type != BackendType.any and backend.backend_type != execution.backend_type:
        return False
    if execution.provider != "auto" and backend.provider != execution.provider:
        return False

    required_gates = {gate for gate in circuit.metadata.gate_names if gate != "barrier"}
    native_gates = set(backend.native_gates)
    if native_gates:
        # A gate is runnable if it is already native OR it is a standard gate the
        # transpiler can decompose into the backend's native basis. Only reject
        # genuinely unknown/custom gates that nothing can map.
        unsupported = {
            gate
            for gate in required_gates
            if gate not in native_gates and gate not in _TRANSPILABLE_GATES
        }
        if unsupported:
            return False

    return True


def _latency_sort_key(backend: BackendCapability) -> tuple[float, float, str, str]:
    queue = backend.queue_time_ms or 0
    return (backend.estimated_latency_ms + queue, queue, backend.provider, backend.backend_name)
