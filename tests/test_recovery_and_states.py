from app.adapters.qiskit_aer_adapter import QiskitAerAdapter
from app.models import (
    BackendRunStatus,
    CircuitFormat,
    CircuitSpec,
    ExecutionOptions,
    ExecutionStrategy,
    JobCreateRequest,
    JobStatus,
)
from app.orchestrator import Orchestrator


def _bell_request(strategy=ExecutionStrategy.benchmark_all):
    return JobCreateRequest(
        name="bell_states_test",
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


def test_benchmark_results_carry_per_backend_status():
    orchestrator = Orchestrator(adapters=[QiskitAerAdapter()])

    result = orchestrator.submit_job(_bell_request(ExecutionStrategy.benchmark_all))

    assert len(result.results) >= 1
    terminal = {BackendRunStatus.completed, BackendRunStatus.failed}
    assert all(run.status in terminal for run in result.results)
    assert any(run.status == BackendRunStatus.completed for run in result.results)


def test_fail_stale_recovers_orphaned_jobs():
    orchestrator = Orchestrator(adapters=[QiskitAerAdapter()])
    repo = orchestrator.repository

    repo.create(job_id="orphan-test-1", name="orphan", request_body={}, strategy="fastest")
    repo.update("orphan-test-1", JobStatus.running)

    # A negative threshold places the cutoff in the future, so any pending/running
    # job counts as stale; the orphaned job must be marked failed.
    recovered = repo.fail_stale(-1)

    assert recovered >= 1
    assert repo.get("orphan-test-1").status == JobStatus.failed
