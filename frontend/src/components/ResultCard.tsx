import type { NormalizedBackendResult } from "../types/quantum";
import CountsChart from "./CountsChart";
import StatusBadge from "./StatusBadge";

export default function ResultCard({ result, highlighted = false }: { result: NormalizedBackendResult; highlighted?: boolean }) {
  return (
    <section className={`rounded-lg border bg-white p-5 shadow-sm ${highlighted ? "border-quantum" : "border-line"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink">{result.backend}</h3>
          <p className="text-sm text-slate-500">{result.provider} · {result.backend_type}</p>
        </div>
        <StatusBadge status={result.status} />
      </div>

      {result.error && (
        <div className="mt-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{result.error}</div>
      )}

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
        <Metric label="Shots" value={result.shots} />
        <Metric label="Execution ms" value={result.metrics.execution_time_ms ?? "n/a"} />
        <Metric label="Depth before" value={result.metrics.depth_before_transpile ?? "n/a"} />
        <Metric label="Depth after" value={result.metrics.depth_after_transpile ?? "n/a"} />
        <Metric label="Qubits" value={result.metrics.num_qubits ?? "n/a"} />
        <Metric label="Operations" value={result.metrics.operation_count ?? "n/a"} />
      </dl>

      <div className="mt-5">
        <h4 className="mb-3 text-sm font-semibold text-slate-700">Measurement counts</h4>
        <CountsChart counts={result.counts} />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md bg-slate-50 p-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-slate-900">{value}</dd>
    </div>
  );
}
