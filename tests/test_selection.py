import pytest

from app.models import (
    BackendCapability,
    BackendType,
    CircuitFormat,
    CircuitMetadata,
    ExecutionOptions,
    ExecutionStrategy,
    InternalCircuit,
)
from app.selection import BackendSelectionError, select_backends


class StaticAdapter:
    def __init__(self, backends):
        self._backends = backends

    def provider_name(self):
        return "static"

    def is_available(self):
        return True

    def capabilities(self):
        return self._backends

    def supports_backend(self, backend_name):
        return any(backend.backend_name == backend_name for backend in self._backends)

    def run(self, job_id, circuit, job_request, backend_capability):
        raise NotImplementedError


def internal_circuit(gates=None, qubits=2):
    gate_names = gates or ["h", "cx", "measure"]
    return InternalCircuit(
        format=CircuitFormat.json,
        num_qubits=qubits,
        num_clbits=qubits,
        operations=[],
        metadata=CircuitMetadata(
            num_qubits=qubits,
            num_clbits=qubits,
            gate_names=gate_names,
            operation_count=len(gate_names),
            has_measurements="measure" in gate_names,
        ),
        raw_source={},
    )


def backend(name, latency, qubits=5, provider="mock", backend_type=BackendType.simulator, gates=None):
    return BackendCapability(
        provider=provider,
        backend_name=name,
        backend_type=backend_type,
        num_qubits=qubits,
        native_gates=gates or ["h", "cx", "measure"],
        topology="test",
        noise_model_available=False,
        estimated_latency_ms=latency,
    )


def test_fastest_backend_selection_uses_lowest_estimated_latency():
    adapter = StaticAdapter([backend("slow", 100), backend("fast", 5)])

    selected = select_backends(
        ExecutionOptions(strategy=ExecutionStrategy.fastest),
        internal_circuit(),
        [adapter],
    )

    assert [item.backend_name for item in selected] == ["fast"]


def test_benchmark_all_strategy_returns_all_compatible_backends():
    adapter = StaticAdapter(
        [
            backend("a", 50, qubits=2),
            backend("too-small", 1, qubits=1),
            backend("b", 60, qubits=3),
        ]
    )

    selected = select_backends(
        ExecutionOptions(strategy=ExecutionStrategy.benchmark_all),
        internal_circuit(qubits=2),
        [adapter],
    )

    assert [item.backend_name for item in selected] == ["a", "b"]


def test_selection_filters_by_provider_and_backend_type():
    adapter = StaticAdapter(
        [
            backend("qiskit-sim", 50, provider="qiskit", backend_type=BackendType.simulator),
            backend("ibm-hw", 20, provider="ibm", backend_type=BackendType.hardware),
        ]
    )

    selected = select_backends(
        ExecutionOptions(strategy=ExecutionStrategy.fastest, provider="ibm", backend_type=BackendType.hardware),
        internal_circuit(),
        [adapter],
    )

    assert selected[0].backend_name == "ibm-hw"


def test_no_compatible_backend_raises_clear_error():
    adapter = StaticAdapter([backend("too-small", 1, qubits=1)])

    with pytest.raises(BackendSelectionError, match="No compatible backend"):
        select_backends(
            ExecutionOptions(strategy=ExecutionStrategy.fastest, min_qubits=4),
            internal_circuit(qubits=4),
            [adapter],
        )


def test_ibm_native_basis_is_compatible_with_high_level_gates():
    # IBM hardware reports only its native basis; h/cx/measure are not listed
    # but are transpilable, so the backend must still be considered compatible.
    ibm_native = backend(
        "ibm_real", 20, qubits=5, provider="ibm",
        backend_type=BackendType.hardware, gates=["ecr", "id", "rz", "sx", "x"],
    )
    adapter = StaticAdapter([ibm_native])

    selected = select_backends(
        ExecutionOptions(strategy=ExecutionStrategy.fastest, provider="ibm",
                         backend_type=BackendType.hardware),
        internal_circuit(gates=["h", "cx", "measure"]),
        [adapter],
    )

    assert selected[0].backend_name == "ibm_real"


def test_truly_unknown_gate_is_still_rejected():
    adapter = StaticAdapter([backend("limited", 10, gates=["ecr", "rz", "sx", "x"])])

    with pytest.raises(BackendSelectionError):
        select_backends(
            ExecutionOptions(strategy=ExecutionStrategy.fastest),
            internal_circuit(gates=["totally_custom_gate"]),
            [adapter],
        )
