import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { quantumApi } from "../api/quantumApi";
import LoadingSpinner from "../components/LoadingSpinner";
import ResultCard from "../components/ResultCard";
import StatusBadge from "../components/StatusBadge";
import type { JobStatus, NormalizedJobResult } from "../types/quantum";

// Jobs run asynchronously on a Celery worker, so the result page polls until the
// job reaches a terminal state. In local synchronous (eager) mode the first
// fetch already returns a terminal status and polling stops immediately.
const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed", "partial"];
const POLL_INTERVAL_MS = 1500;

export default function ResultPage() {
  const { jobId } = useParams();
  const [result, setResult] = useState<NormalizedJobResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!jobId) {
      setError("No job id was provided.");
      setLoading(false);
      return;
    }

    let cancelled = false;

    const poll = () => {
      quantumApi.result(jobId)
        .then((data) => {
          if (cancelled) return;
          setResult(data);
          setError(null);
          if (!TERMINAL_STATUSES.includes(data.status)) {
            timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
          }
        })
        .catch((err: Error) => {
          if (!cancelled) setError(err.message);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    };

    setLoading(true);
    poll();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [jobId]);

  if (loading) return <LoadingSpinner label="Loading result" />;
  if (error) return <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  if (!result) return <div className="rounded-lg border border-line bg-white p-6 text-sm text-slate-600">Result not found.</div>;

  const isRunning = !TERMINAL_STATUSES.includes(result.status);

  return (
    <div className="space-y-6">
      <header className="rounded-lg border border-line bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-ink">Job result</h1>
            <p className="mt-2 font-mono text-xs text-slate-500">{result.job_id}</p>
            <p className="mt-2 text-sm text-slate-600">{result.name ?? "untitled"} · {result.strategy}</p>
          </div>
          <StatusBadge status={result.status} />
        </div>
      </header>

      {isRunning && (
        <div className="flex items-center gap-3 rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">
          <span className="h-3 w-3 animate-pulse rounded-full bg-sky-500" />
          <span>Job is {result.status}. This page refreshes automatically every {POLL_INTERVAL_MS / 1000}s…</span>
        </div>
      )}

      {result.errors.length > 0 && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 text-sm text-orange-800">
          <p className="font-semibold">Backend errors</p>
          <ul className="mt-2 list-disc pl-5">
            {result.errors.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )}

      {result.results.length === 0 && (
        <div className="rounded-lg border border-line bg-white p-6 text-sm text-slate-600">No backend results were returned.</div>
      )}

      {result.strategy === "fastest" && result.results[0] && <ResultCard result={result.results[0]} highlighted />}

      {result.strategy === "benchmark_all" && (
        <>
          <ComparisonTable result={result} />
          <div className="grid gap-4 lg:grid-cols-2">
            {result.results.map((backendResult) => (
              <ResultCard key={`${backendResult.provider}-${backendResult.backend}`} result={backendResult} />
            ))}
          </div>
        </>
      )}

      <Link className="btn-secondary inline-flex" to="/jobs">Back to jobs</Link>
    </div>
  );
}

function ComparisonTable({ result }: { result: NormalizedJobResult }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-white shadow-sm">
      <div className="border-b border-line px-4 py-3">
        <h2 className="font-semibold text-ink">Benchmark comparison</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-line text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Backend</th>
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Execution ms</th>
              <th className="px-4 py-3">Depth before</th>
              <th className="px-4 py-3">Depth after</th>
              <th className="px-4 py-3">Counts</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {result.results.map((item) => (
              <tr key={`${item.provider}-${item.backend}`}>
                <td className="px-4 py-3">{item.backend}</td>
                <td className="px-4 py-3">{item.provider}</td>
                <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                <td className="px-4 py-3">{item.metrics.execution_time_ms ?? "n/a"}</td>
                <td className="px-4 py-3">{item.metrics.depth_before_transpile ?? "n/a"}</td>
                <td className="px-4 py-3">{item.metrics.depth_after_transpile ?? "n/a"}</td>
                <td className="px-4 py-3 font-mono text-xs">{JSON.stringify(item.counts)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
