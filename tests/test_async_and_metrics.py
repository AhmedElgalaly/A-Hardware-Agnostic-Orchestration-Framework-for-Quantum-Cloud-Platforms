from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _bell_job(strategy: str = "fastest") -> dict:
    return {
        "name": "bell_metrics",
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
        "shots": 128,
        "execution": {"strategy": strategy},
    }


def test_metrics_endpoint_is_exposed():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "qaas_jobs_submitted_total" in response.text or "# HELP" in response.text


def test_job_metrics_increment_after_submission():
    client.post("/jobs", json=_bell_job("benchmark_all"))
    metrics = client.get("/metrics").text

    assert "qaas_jobs_submitted_total" in metrics
    assert 'qaas_jobs_finished_total{' in metrics
    assert 'qaas_backend_runs_total{' in metrics
    assert 'provider="qiskit"' in metrics


def test_eager_submission_completes_synchronously():
    response = client.post("/jobs", json=_bell_job("fastest"))
    assert response.status_code == 202
    body = response.json()
    # In local eager mode the job is already finished when the POST returns.
    assert body["status"] == "completed"

    result = client.get(body["result_url"]).json()
    assert result["results"][0]["provider"] == "qiskit"
    assert sum(result["results"][0]["counts"].values()) == 128
