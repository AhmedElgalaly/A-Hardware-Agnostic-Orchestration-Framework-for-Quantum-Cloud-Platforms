from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


BELL_QASM = (
    'OPENQASM 2.0; include "qelib1.inc"; '
    "qreg q[2]; creg c[2]; h q[0]; cx q[0], q[1]; measure q -> c;"
)


def test_root_health_and_backends():
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}

    backends = client.get("/backends")
    assert backends.status_code == 200
    assert any(backend["provider"] == "qiskit" and backend["backend_name"] == "aer_simulator" for backend in backends.json())


def test_cors_allows_local_frontend_origin():
    response = client.options(
        "/backends",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_openqasm_bell_state_job_fastest():
    response = client.post(
        "/jobs",
        json={
            "name": "bell_openqasm_test",
            "circuit": {"format": "openqasm2", "source": BELL_QASM},
            "shots": 64,
            "execution": {"strategy": "fastest", "backend_type": "any", "provider": "auto", "min_qubits": 2},
        },
    )

    assert response.status_code == 202
    result = client.get(response.json()["result_url"]).json()
    assert result["strategy"] == "fastest"
    assert len(result["results"]) == 1
    assert_normalized_result(result)


def test_json_bell_state_job_benchmark_all():
    response = client.post(
        "/jobs",
        json={
            "name": "bell_json_test",
            "circuit": {
                "format": "json",
                "qubits": 2,
                "classical_bits": 2,
                "gates": [
                    {"name": "h", "targets": [0]},
                    {"name": "cx", "controls": [0], "targets": [1]},
                    {"name": "measure", "targets": [0, 1]},
                ],
            },
            "shots": 64,
            "execution": {"strategy": "benchmark_all", "backend_type": "any", "provider": "auto", "min_qubits": 2},
        },
    )

    assert response.status_code == 202
    result = client.get(response.json()["result_url"]).json()
    assert result["strategy"] == "benchmark_all"
    assert any(run["backend"] == "aer_simulator" for run in result["results"])
    assert_normalized_result(result)


def test_invalid_circuit_format_returns_validation_error():
    response = client.post(
        "/jobs",
        json={
            "name": "bad_format",
            "circuit": {"format": "qasm3", "source": "bad"},
            "shots": 32,
            "execution": {"strategy": "fastest"},
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()


def test_insufficient_qubits_returns_no_compatible_backend_error():
    response = client.post(
        "/jobs",
        json={
            "name": "too_many_qubits",
            "circuit": {
                "format": "json",
                "qubits": 2,
                "gates": [{"name": "measure", "targets": [0, 1]}],
            },
            "shots": 32,
            "execution": {"strategy": "fastest", "min_qubits": 1000},
        },
    )

    assert response.status_code == 422
    assert "No compatible backend" in response.json()["detail"]


def test_job_listing_and_rerun():
    created = client.post(
        "/jobs",
        json={
            "name": "rerun_target",
            "circuit": {
                "format": "json",
                "qubits": 1,
                "gates": [{"name": "measure", "targets": [0]}],
            },
            "shots": 8,
            "execution": {"strategy": "fastest"},
        },
    ).json()

    assert client.get("/jobs").status_code == 200
    assert client.get(f"/jobs/{created['job_id']}").status_code == 200

    rerun = client.post(f"/jobs/{created['job_id']}/rerun")
    assert rerun.status_code == 202
    assert rerun.json()["job_id"] != created["job_id"]


def assert_normalized_result(payload):
    assert {"job_id", "name", "strategy", "status", "results", "errors", "created_at", "updated_at"}.issubset(payload)
    run = payload["results"][0]
    assert {"provider", "backend", "backend_type", "status", "shots", "counts", "metrics", "error"}.issubset(run)
    assert {
        "execution_time_ms",
        "depth_before_transpile",
        "depth_after_transpile",
        "num_qubits",
        "operation_count",
        "selected_backend",
        "provider",
        "status",
        "timestamp",
    }.issubset(run["metrics"])
