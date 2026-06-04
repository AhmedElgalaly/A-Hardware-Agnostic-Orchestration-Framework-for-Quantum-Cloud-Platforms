import { FormEvent, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { quantumApi } from "../api/quantumApi";
import LoadingSpinner from "../components/LoadingSpinner";
import type { BackendType, CircuitFormat, ExecutionStrategy, JobRequest } from "../types/quantum";

const openQasmExample = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0]; cx q[0], q[1]; measure q -> c;';
const jsonExample = JSON.stringify(
  {
    qubits: 2,
    classical_bits: 2,
    gates: [
      { name: "h", targets: [0] },
      { name: "cx", controls: [0], targets: [1] },
      { name: "measure", targets: [0, 1] }
    ]
  },
  null,
  2
);

export default function SubmitJobPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("bell_state_frontend");
  const [format, setFormat] = useState<CircuitFormat>("openqasm2");
  const [editor, setEditor] = useState(openQasmExample);
  const [shots, setShots] = useState(1024);
  const [strategy, setStrategy] = useState<ExecutionStrategy>("fastest");
  const [backendType, setBackendType] = useState<BackendType>("any");
  const [provider, setProvider] = useState("auto");
  const [objective, setObjective] = useState("min_latency");
  const [minQubits, setMinQubits] = useState(2);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const strategyHelp = useMemo(
    () =>
      strategy === "fastest"
        ? "The framework selects the compatible backend with the lowest estimated latency."
        : "The framework runs the same circuit on all compatible available backends and returns comparable results.",
    [strategy]
  );

  function switchFormat(nextFormat: CircuitFormat) {
    setFormat(nextFormat);
    setEditor(nextFormat === "openqasm2" ? openQasmExample : jsonExample);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const requestBody = buildRequest();
      const response = await quantumApi.submitJob(requestBody);
      setMessage(`Job ${response.job_id} submitted (${response.status}). Opening result page.`);
      navigate(`/results/${response.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit job.");
    } finally {
      setLoading(false);
    }
  }

  function buildRequest(): JobRequest {
    if (format === "openqasm2") {
      return {
        name,
        circuit: { format, source: editor },
        shots,
        execution: { strategy, backend_type: backendType, provider, objective, min_qubits: minQubits }
      };
    }

    let parsed: { qubits?: number; classical_bits?: number; gates?: unknown[] };
    try {
      parsed = JSON.parse(editor);
    } catch {
      throw new Error("JSON circuit is not valid JSON.");
    }

    return {
      name,
      circuit: {
        format,
        qubits: parsed.qubits,
        classical_bits: parsed.classical_bits,
        gates: parsed.gates as JobRequest["circuit"]["gates"]
      },
      shots,
      execution: { strategy, backend_type: backendType, provider, objective, min_qubits: minQubits }
    };
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-ink">Submit quantum job</h1>
        <p className="mt-2 text-sm text-slate-600">Provider credentials are not requested here. Cloud credentials stay backend-side.</p>
      </header>

      <form onSubmit={handleSubmit} className="rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="grid gap-5 lg:grid-cols-3">
          <Field label="Job name">
            <input className="input" value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Circuit format">
            <select className="input" value={format} onChange={(event) => switchFormat(event.target.value as CircuitFormat)}>
              <option value="openqasm2">openqasm2</option>
              <option value="json">json</option>
            </select>
          </Field>
          <Field label="Shots">
            <input className="input" type="number" min={1} value={shots} onChange={(event) => setShots(Number(event.target.value))} />
          </Field>
        </div>

        <div className="mt-5">
          <label className="label">Circuit editor</label>
          <textarea className="input mt-2 min-h-64 font-mono text-sm" value={editor} onChange={(event) => setEditor(event.target.value)} />
        </div>

        <div className="mt-5 grid gap-5 lg:grid-cols-5">
          <Field label="Strategy">
            <select className="input" value={strategy} onChange={(event) => setStrategy(event.target.value as ExecutionStrategy)}>
              <option value="fastest">fastest</option>
              <option value="benchmark_all">benchmark_all</option>
            </select>
          </Field>
          <Field label="Backend type">
            <select className="input" value={backendType} onChange={(event) => setBackendType(event.target.value as BackendType)}>
              <option value="any">any</option>
              <option value="simulator">simulator</option>
              <option value="hardware">hardware</option>
            </select>
          </Field>
          <Field label="Provider">
            <select className="input" value={provider} onChange={(event) => setProvider(event.target.value)}>
              <option value="auto">auto</option>
              <option value="qiskit">qiskit</option>
              <option value="ibm">ibm</option>
              <option value="aws_braket">aws_braket</option>
              <option value="azure_quantum">azure_quantum</option>
            </select>
          </Field>
          <Field label="Objective">
            <select className="input" value={objective} onChange={(event) => setObjective(event.target.value)}>
              <option value="min_latency">min_latency</option>
              <option value="max_fidelity">max_fidelity</option>
              <option value="min_cost">min_cost</option>
              <option value="compare">compare</option>
            </select>
          </Field>
          <Field label="Minimum qubits">
            <input className="input" type="number" min={1} value={minQubits} onChange={(event) => setMinQubits(Number(event.target.value))} />
          </Field>
        </div>

        <p className="mt-4 rounded-md bg-slate-50 p-3 text-sm text-slate-600">{strategyHelp}</p>

        {error && <div className="mt-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
        {message && <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}

        <div className="mt-6 flex items-center gap-4">
          <button className="btn-primary" type="submit" disabled={loading}>
            Submit job
          </button>
          {loading && <LoadingSpinner label="Submitting job" />}
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label>
      <span className="label">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
  );
}
