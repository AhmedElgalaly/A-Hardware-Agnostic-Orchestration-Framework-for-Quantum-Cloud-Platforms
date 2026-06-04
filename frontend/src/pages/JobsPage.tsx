import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { quantumApi } from "../api/quantumApi";
import LoadingSpinner from "../components/LoadingSpinner";
import StatusBadge from "../components/StatusBadge";
import type { JobSummary, NormalizedJobResult } from "../types/quantum";

export default function JobsPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [details, setDetails] = useState<Record<string, NormalizedJobResult>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    setLoading(true);
    setError(null);
    try {
      const summaries = await quantumApi.jobs();
      setJobs(summaries);
      const detailEntries = await Promise.all(
        summaries.slice(0, 25).map(async (job) => [job.job_id, await quantumApi.job(job.job_id)] as const)
      );
      setDetails(Object.fromEntries(detailEntries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load jobs.");
    } finally {
      setLoading(false);
    }
  }

  async function rerun(jobId: string) {
    try {
      const response = await quantumApi.rerun(jobId);
      navigate(`/results/${response.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to rerun job.");
    }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ink">Jobs</h1>
          <p className="mt-2 text-sm text-slate-600">Review persisted jobs, inspect results, or rerun prior requests.</p>
        </div>
        <button className="btn-secondary" onClick={loadJobs}>Refresh</button>
      </header>

      {loading && <LoadingSpinner label="Loading jobs" />}
      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}
      {!loading && !error && jobs.length === 0 && (
        <div className="rounded-lg border border-line bg-white p-6 text-sm text-slate-600">No jobs yet. Submit a circuit to create the first job.</div>
      )}
      {!loading && jobs.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-line bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-line text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Job ID</th>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Strategy</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Selected backend</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {jobs.map((job) => {
                  const selectedBackend = details[job.job_id]?.results?.[0]?.backend ?? "n/a";
                  return (
                    <tr key={job.job_id}>
                      <td className="px-4 py-3 font-mono text-xs">{job.job_id}</td>
                      <td className="px-4 py-3">{job.name ?? "untitled"}</td>
                      <td className="px-4 py-3">{job.strategy}</td>
                      <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                      <td className="px-4 py-3">{new Date(job.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3">{selectedBackend}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Link className="btn-secondary" to={`/results/${job.job_id}`}>View result</Link>
                          <button className="btn-secondary" onClick={() => rerun(job.job_id)}>Rerun</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
