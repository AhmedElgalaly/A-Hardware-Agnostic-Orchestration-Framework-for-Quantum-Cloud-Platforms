import pytest

from app.adapters.qiskit_aer_adapter import QiskitAerAdapter
from app.models import BackendCapability, BackendType, CircuitFormat, CircuitSpec, ExecutionOptions, ExecutionStrategy, JobCreateRequest
from app.orchestrator import Orchestrator
from app.selection import BackendSelectionError


BELL_QASM = (
    'OPENQASM 2.0; include "qelib1.inc"; '
    "qreg q[2]; creg c[2]; h q[0]; cx q[0], q[1]; measure q -> c;"
)


def json_bell_request(strategy=ExecutionStrategy.fastest):
    return JobCreateRequest(
        name="bell_json_test",
        circuit=CircuitSpec(
            format=CircuitFormat.json,
            qubits=2,
            classical_bits=2,
            gates=[
                {"name": "h", "targets": [0]},
                {"name": "cx", "controls": [0], "targets": [1]},
                {"name": "measure", "targets": [0, 1]},
            ],
        ),
        shots=64,
        execution=ExecutionOptions(strategy=strategy),
    )


def test_orchestrator_fastest_returns_one_normalized_result():
    orchestrator = Orchestrator(adapters=[QiskitAerAdapter()])

    result = orchestrator.submit_job(json_bell_request())

    assert result.status == "completed"
    assert result.strategy == "fastest"
    assert len(result.results) == 1
    assert result.results[0].provider == "qiskit"
    assert result.results[0].backend == "aer_simulator"
    assert sum(result.results[0].counts.values()) == 64


def test_orchestrator_benchmark_all_returns_at_least_qiskit_aer_result():
    orchestrator = Orchestrator(adapters=[QiskitAerAdapter()])

    result = orchestrator.submit_job(json_bell_request(ExecutionStrategy.benchmark_all))

    assert result.status == "completed"
    assert len(result.results) >= 1
    assert any(run.backend == "aer_simulator" for run in result.results)


def test_orchestrator_persists_and_retrieves_result():
    orchestrator = Orchestrator(adapters=[QiskitAerAdapter()])
    created = orchestrator.submit_job(json_bell_request())

    stored = orchestrator.get_result(created.job_id)

    assert stored.job_id == created.job_id
    assert stored.results[0].backend == "aer_simulator"


def test_orchestrator_no_compatible_backend_error():
    orchestrator = Orchestrator(adapters=[QiskitAerAdapter()])
    request = json_bell_request()
    request.execution.min_qubits = 1000

    with pytest.raises(BackendSelectionError):
        orchestrator.submit_job(request)


def test_benchmark_all_returns_partial_result_when_one_backend_raises():
    orchestrator = Orchestrator(adapters=[QiskitAerAdapter(), RaisingAdapter()])

    result = orchestrator.submit_job(json_bell_request(ExecutionStrategy.benchmark_all))

    assert result.status == "partial"
    assert any(run.status == "completed" and run.backend == "aer_simulator" for run in result.results)
    assert any(run.status == "failed" and run.backend == "raising_backend" for run in result.results)
    assert result.errors


class RaisingAdapter:
    def provider_name(self):
        return "raising"

    def is_available(self):
        return True

    def capabilities(self):
        return [
            BackendCapability(
                provider="raising",
                backend_name="raising_backend",
                backend_type=BackendType.simulator,
                num_qubits=2,
                native_gates=["h", "cx", "measure"],
                topology="test",
                noise_model_available=False,
                estimated_latency_ms=60,
            )
        ]

    def supports_backend(self, backend_name):
        return backend_name == "raising_backend"

    def run(self, job_id, circuit, job_request, backend_capability):
        raise RuntimeError("simulated backend failure")
