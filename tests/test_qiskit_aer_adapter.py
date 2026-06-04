from app.adapters.qiskit_aer_adapter import QiskitAerAdapter
from app.models import BackendRunStatus, CircuitFormat, CircuitSpec, ExecutionOptions, JobCreateRequest
from app.parser import translate_circuit


def test_qiskit_aer_capabilities():
    adapter = QiskitAerAdapter()
    capability = adapter.capabilities()[0]

    assert adapter.is_available() is True
    assert capability.provider == "qiskit"
    assert capability.backend_name == "aer_simulator"
    assert capability.backend_type == "simulator"
    assert capability.num_qubits >= 32
    assert {"h", "cx", "measure"}.issubset(set(capability.native_gates))


def test_qiskit_aer_execution_returns_normalized_result():
    request = JobCreateRequest(
        name="x_gate_test",
        circuit=CircuitSpec(
            format=CircuitFormat.json,
            qubits=1,
            gates=[
                {"name": "x", "targets": [0]},
                {"name": "measure", "targets": [0]},
            ],
        ),
        shots=32,
        execution=ExecutionOptions(),
    )
    adapter = QiskitAerAdapter()

    result = adapter.run("job-1", translate_circuit(request.circuit), request, adapter.capabilities()[0])

    assert result.status == BackendRunStatus.completed
    assert result.provider == "qiskit"
    assert result.backend == "aer_simulator"
    assert result.shots == 32
    assert result.counts == {"1": 32}
    assert result.metrics.execution_time_ms is not None
    assert result.metrics.depth_before_transpile is not None
    assert result.metrics.depth_after_transpile is not None
