# A Hardware-Agnostic Orchestration Framework for Quantum Cloud Platforms

This project proposes a hardware-agnostic orchestration framework for quantum cloud platforms. It allows researchers and developers to submit quantum circuits in OpenQASM or JSON format and execute them either on the fastest compatible backend or across all compatible backends for benchmarking. The framework abstracts provider-specific SDKs through adapters, models backend capabilities, normalizes results, and helps researchers compare heterogeneous quantum systems more easily.

> **Local-first, no authentication.** This is a single-researcher tool meant to run on your own machine. There is no login, no API keys, and no user management — the goal is to make a researcher's life easier, not to operate a multi-tenant service. Jobs run asynchronously through a Celery worker (with a synchronous fallback for quick local runs), and a Prometheus + Grafana stack provides monitoring. Provider credentials live only in a local `.env` file and are never exposed by the API.

Quantum cloud platforms are fragmented because each provider exposes different SDKs, authentication methods, backend names, queue behavior, hardware topology, native gates, simulators, and result formats. Researchers often need to compare candidate backends before committing experiments to real hardware, especially because real devices differ in noise, queue time, connectivity, and supported operations. This prototype gives one API for circuit submission, backend discovery, execution strategy selection, persistence, and normalized result retrieval.

## Architecture

```text
app/
  main.py                       FastAPI routes + Prometheus /metrics
  models.py                     Pydantic request, backend, job, result models
  database.py                   SQLite connection and schema (WAL for multi-process)
  repository.py                 Job persistence
  orchestrator.py               End-to-end job workflow + metric recording
  celery_app.py                 Celery application (async execution)
  tasks.py                      Background job task executed by the worker
  observability.py              Prometheus counters/histograms for jobs & backends
  parser.py                     OpenQASM 2 and JSON parsing
  selection.py                  Backend compatibility and strategy selection
  metrics.py                    Timing helper
  config.py                     Environment-backed settings
  adapters/
    base.py                     Provider adapter interface
    qiskit_aer_adapter.py       Working local simulator adapter
    ibm_quantum_adapter.py      IBM Quantum adapter (SamplerV2 primitives)
    aws_braket_adapter.py       AWS Braket adapter (amazon-braket-sdk)
    azure_quantum_adapter.py    Azure Quantum adapter (azure-quantum Qiskit provider)
  services/
    circuit_translator.py       Internal model to Qiskit translation
    result_normalizer.py        Common result schema
monitoring/
  prometheus.yml                Scrape config for the API and the worker
  grafana/                      Auto-provisioned datasource + U-QaaS dashboard
```

The deployable stack (`docker compose`) runs six services: the **FastAPI API**, a **Celery worker**, **Redis** (broker + result backend), **Prometheus**, **Grafana**, and the **React frontend**.

The workflow is:

1. A user submits one circuit in OpenQASM 2 or JSON format.
2. `parser.py` converts the input into a provider-independent `InternalCircuit`.
3. `circuit_translator.py` converts the internal model to a Qiskit `QuantumCircuit` for the working local adapter.
4. Adapters expose backend capabilities using a shared schema.
5. `selection.py` filters by qubits, backend type, provider, and gate support.
6. `fastest` selects the compatible backend with the lowest estimated latency.
7. `benchmark_all` runs every compatible available backend.
8. Results are normalized into one schema and stored in SQLite.

## Backend Capability Modeling

Each backend reports:

- provider name
- backend name
- backend type: `simulator` or `hardware`
- number of qubits
- native gate set
- topology or connectivity description
- noise model availability
- estimated latency
- optional queue time, fidelity, coupling map, and metadata

This makes heterogeneous quantum systems comparable before execution.

## Result Normalization

Provider SDKs return different result shapes. This framework normalizes every backend result to:

- provider
- backend
- backend type
- per-backend status
- shots
- counts
- metrics
- error, if execution failed

Metrics include execution time, transpilation depth before and after, qubit count, operation count, selected backend, provider, status, and timestamp.

## Providers

### Qiskit Aer

Qiskit Aer is the default working adapter because it provides reliable local testing without cloud credentials, queues, or hardware noise. It exposes `qiskit/aer_simulator` as a simulator backend with low estimated latency, at least 32 qubits, and common gates such as `h`, `x`, `rx`, `cx`, `cz`, and `measure`.

### IBM Quantum

The IBM adapter is optional. If `qiskit-ibm-runtime` and credentials are available, it can discover IBM backends. If the adapter is disabled or credentials are missing, `is_available()` returns false and the app continues to run locally with Qiskit Aer.

Enable IBM only on the backend:

```bash
ENABLE_IBM=true
IBM_QUANTUM_TOKEN=your_token
IBM_INSTANCE=your_hub/group/project
```

Real hardware execution is subject to provider availability, credentials, queues, calibration, and device noise.

Provider credentials are backend-side secrets. They must never be sent to the frontend, returned by `/backends`, logged, or stored in SQLite. Storing per-user provider credentials is future work and would require an encrypted credential vault design with access control, audit logging, and key rotation.

### AWS Braket

The AWS Braket adapter uses `amazon-braket-sdk`. Enable it with `ENABLE_AWS_BRAKET=true`, AWS credentials, a region, and an S3 bucket for results:

```bash
ENABLE_AWS_BRAKET=true
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_BRAKET_S3_BUCKET=your-braket-bucket
```

It exposes the managed simulators (SV1, DM1, TN1) and discovers online QPUs. Braket usage is billed per shot.

### Azure Quantum

The Azure Quantum adapter uses the `azure-quantum` Qiskit provider. Enable it with `ENABLE_AZURE_QUANTUM=true` and your workspace coordinates:

```bash
ENABLE_AZURE_QUANTUM=true
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP=...
AZURE_WORKSPACE_NAME=...
AZURE_LOCATION=...
# optional service principal:
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
```

Targets (IonQ, Quantinuum, Rigetti, simulators) are discovered from the workspace. Azure usage is billed by the provider.

> The provider SDKs (`qiskit-ibm-runtime`, `amazon-braket-sdk`, `azure-quantum`) are listed but commented out in `requirements.txt`. Install the ones you need; without them the corresponding adapter simply reports itself unavailable and the platform keeps running on the other backends.

## Install

Recommended local setup:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

You can also run:

```bash
python run.py
```

## Run the Frontend

The React frontend is in `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at:

```text
http://127.0.0.1:8000
```

Configure this with `frontend/.env`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The frontend never asks for IBM, AWS, or Azure credentials. Provider tokens remain backend-side only.

Configuration is environment-based. Common settings:

```bash
APP_ENV=development
DATABASE_URL=sqlite:///./quantum_jobs.db
HOST=127.0.0.1
PORT=8000
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Copy `.env.example` to `.env` for local development if you want to override defaults. Never commit `.env`.

For frontend development, CORS is enabled for:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Override these with `FRONTEND_ORIGINS` as a comma-separated list. Wildcard origins (`*`) are filtered out in production mode.

## Docker

Build the image:

```bash
docker build -t quantum-orchestrator .
```

Run the container:

```bash
docker run --rm -p 8000:8000 -v quantum-orchestrator-data:/data quantum-orchestrator
```

Run the full stack with Docker Compose:

```bash
cp .env.example .env   # fill in provider credentials only if you want real hardware
docker compose up --build
```

Docker Compose starts the complete local platform:

- Backend API: `http://127.0.0.1:8000` (docs at `/docs`, metrics at `/metrics`)
- Frontend UI: `http://127.0.0.1:5173`
- Celery worker: executes jobs asynchronously, exports worker metrics on `:9100`
- Redis: `localhost:6379` (Celery broker + result backend)
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000` (login `admin` / `admin`, dashboard "U-QaaS Orchestration" auto-provisioned)

The backend and worker share SQLite data at `/data/quantum_jobs.db` via the `quantum-orchestrator-data` named volume.

### Run locally without Docker (synchronous, no broker)

For a quick local run with no Redis or worker, set `CELERY_TASK_ALWAYS_EAGER=true` in `.env` and jobs execute synchronously inside the API process:

```bash
CELERY_TASK_ALWAYS_EAGER=true uvicorn app.main:app --reload
```

To run the async path manually (two terminals), start Redis, then:

```bash
celery -A app.celery_app worker --loglevel=info --pool=solo   # terminal 1
uvicorn app.main:app --reload                                  # terminal 2
```

Open:

```text
http://127.0.0.1:5173
```

Backend API docs remain available at:

```text
http://127.0.0.1:8000/docs
```

## API

- `GET /`
- `GET /health`
- `GET /backends`
- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/result`
- `POST /jobs/{job_id}/rerun`

## Defense Walkthrough

For a graduation project defense, a concise demo flow is:

1. Open `http://127.0.0.1:8000/docs` and show that the API is unified around jobs and backends.
2. Call `GET /backends` and explain backend capability modeling: provider, backend type, qubits, gates, topology, noise availability, and estimated latency.
3. Submit `examples/bell_openqasm.json` to demonstrate OpenQASM input.
4. Submit `examples/bell_json_circuit.json` to demonstrate JSON input and internal circuit translation.
5. Submit `examples/benchmark_all_example.json` and explain how one circuit can be executed on all compatible available backends.
6. Call `GET /jobs/{job_id}/result` and explain result normalization: the schema stays the same regardless of provider.
7. Mention that Qiskit Aer is the reliable local simulator, IBM Quantum is optional, and AWS/Azure are extension points.

Key talking points:

- The project does not claim quantum advantage. It solves orchestration, portability, and comparison across fragmented quantum cloud providers.
- `fastest` mode chooses the compatible backend with the lowest estimated latency.
- `benchmark_all` mode is designed for research comparison and tolerates per-backend failures.
- SQLite persistence makes job results retrievable after submission.
- The adapter interface is the main extensibility boundary.

## Example Requests

List backends:

```bash
curl http://127.0.0.1:8000/backends
```

OpenQASM Bell state using fastest mode:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d @examples/bell_openqasm.json
```

JSON Bell state:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d @examples/bell_json_circuit.json
```

Benchmark all compatible available backends:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d @examples/benchmark_all_example.json
```

Retrieve a result:

```bash
curl http://127.0.0.1:8000/jobs/<job_id>/result
```

Rerun a saved job:

```bash
curl -X POST http://127.0.0.1:8000/jobs/<job_id>/rerun
```

## Input Formats

OpenQASM 2:

```json
{
  "name": "bell_state_test",
  "circuit": {
    "format": "openqasm2",
    "source": "OPENQASM 2.0; include \"qelib1.inc\"; qreg q[2]; creg c[2]; h q[0]; cx q[0], q[1]; measure q -> c;"
  },
  "shots": 1024,
  "execution": {
    "strategy": "fastest",
    "backend_type": "any",
    "provider": "auto",
    "objective": "min_latency",
    "min_qubits": 2
  }
}
```

JSON circuit:

```json
{
  "name": "bell_json_test",
  "circuit": {
    "format": "json",
    "qubits": 2,
    "classical_bits": 2,
    "gates": [
      {"name": "h", "targets": [0]},
      {"name": "cx", "controls": [0], "targets": [1]},
      {"name": "measure", "targets": [0, 1]}
    ]
  },
  "shots": 1024,
  "execution": {
    "strategy": "benchmark_all",
    "backend_type": "any",
    "provider": "auto",
    "objective": "compare",
    "min_qubits": 2
  }
}
```

Supported JSON gates: `h`, `x`, `y`, `z`, `rx`, `ry`, `rz`, `cx`, `cz`, and `measure`.

## Testing

```bash
pytest
```

Tests pass without IBM, AWS, or Azure credentials. Local execution uses Qiskit Aer.

The current tests cover:

- OpenQASM Bell-state parsing and execution.
- JSON Bell-state parsing and execution.
- Fastest-mode selection.
- Benchmark-all selection and partial backend failure handling.
- Qiskit Aer execution.
- Invalid input and no-compatible-backend errors.
- Normalized result schema.
- Optional IBM/AWS/Azure adapter behavior.

## Troubleshooting

- If `POST /jobs` returns `422`, check that `circuit.format` is `openqasm2` or `json`, `execution.strategy` is `fastest` or `benchmark_all`, and JSON circuits use `gates`.
- If no backend is compatible, lower `execution.min_qubits`, use `backend_type: "any"`, or verify the gate set is supported by Qiskit Aer.
- If Docker cannot build, make sure Docker Desktop is running with the Linux engine enabled.
- Delete `quantum_jobs.db` to reset local job history.

## Future Work

- Add provider-specific transpilation policies and circuit optimization passes.
- Add richer cost, fidelity, and queue-time selection objectives.
- Add frontend dashboards for benchmark comparison (Grafana covers system metrics today).
- Support `prometheus_client` multiprocess mode for multi-worker metric aggregation.
- Optional authentication layer if the tool is ever deployed for multiple users (out of scope for the current local-first design).
