# Quantum Orchestrator Frontend

React + Vite + TypeScript frontend for **A Hardware-Agnostic Orchestration Framework for Quantum Cloud Platforms**.

The frontend lets users submit OpenQASM 2 or JSON quantum circuits, choose `fastest` or `benchmark_all` execution, inspect available backends, view job history, and compare normalized results.

Provider credentials are not handled by the frontend. IBM/AWS/Azure credentials remain backend-side only through backend environment variables.

## Install

```bash
npm install
```

## Configure

Create a local `.env` from `.env.example` if needed:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The FastAPI backend should be running at:

```text
http://127.0.0.1:8000
```

## Run

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Docker

From the repository root, run both backend and frontend:

```bash
docker compose up --build
```

The frontend is served by Nginx at:

```text
http://127.0.0.1:5173
```

The Compose build passes:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Example Workflow

1. Start the backend:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Start the frontend:
   ```bash
   npm run dev
   ```
3. Open the Dashboard and confirm backend health.
4. Submit the OpenQASM Bell circuit on the Submit Job page.
5. Run `fastest` mode and view the highlighted result card.
6. Run `benchmark_all` mode and view the backend comparison table.
7. Review persisted jobs on the Jobs page.
