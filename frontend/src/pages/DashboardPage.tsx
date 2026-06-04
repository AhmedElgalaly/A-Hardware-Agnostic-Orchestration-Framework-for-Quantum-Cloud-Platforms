import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowRight, Database, FilePlus2, History } from "lucide-react";
import { quantumApi } from "../api/quantumApi";
import LoadingSpinner from "../components/LoadingSpinner";
import StatusBadge from "../components/StatusBadge";

export default function DashboardPage() {
  const [health, setHealth] = useState<string>("loading");
  const [backendCount, setBackendCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([quantumApi.health(), quantumApi.backends()])
      .then(([healthResponse, backends]) => {
        setHealth(healthResponse.status);
        setBackendCount(backends.length);
      })
      .catch((err: Error) => {
        setHealth("failed");
        setError(err.message);
      });
  }, []);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-line bg-white p-6 shadow-sm">
        <p className="mb-2 text-sm font-medium uppercase tracking-wide text-quantum">Graduation Project Prototype</p>
        <h1 className="max-w-4xl text-3xl font-bold tracking-tight text-ink">
          A Hardware-Agnostic Orchestration Framework for Quantum Cloud Platforms
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
          Submit quantum circuits in OpenQASM or JSON, execute them on the fastest compatible backend, or benchmark them
          across all compatible available backends.
        </p>
      </section>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-line bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-ink">Backend health</h2>
            {health === "loading" ? <LoadingSpinner label="Checking" /> : <StatusBadge status={health} />}
          </div>
          <p className="mt-3 text-sm text-slate-600">The frontend checks `GET /health` before users submit work.</p>
        </div>
        <div className="rounded-lg border border-line bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-ink">Available backends</h2>
            <span className="text-2xl font-bold text-quantum">{backendCount ?? "..."}</span>
          </div>
          <p className="mt-3 text-sm text-slate-600">Backends are discovered through provider adapters on the backend.</p>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <QuickLink to="/submit" icon={FilePlus2} title="Submit Job" text="Upload OpenQASM or JSON circuits." />
        <QuickLink to="/backends" icon={Database} title="Backends" text="Inspect providers and capabilities." />
        <QuickLink to="/jobs" icon={History} title="Jobs" text="Review persisted job history." />
        <QuickLink to="/results" icon={Activity} title="Results" text="Open prior normalized results." />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <InfoCard
          title="Fastest mode"
          text="The framework selects the compatible backend with the lowest estimated latency."
        />
        <InfoCard
          title="Benchmark-all mode"
          text="The framework runs the same circuit on all compatible available backends and returns comparable results."
        />
      </section>
    </div>
  );
}

function QuickLink({ to, icon: Icon, title, text }: { to: string; icon: typeof FilePlus2; title: string; text: string }) {
  return (
    <Link to={to} className="rounded-lg border border-line bg-white p-5 shadow-sm transition hover:border-quantum">
      <Icon className="h-5 w-5 text-quantum" />
      <div className="mt-4 flex items-center justify-between gap-3">
        <h3 className="font-semibold text-ink">{title}</h3>
        <ArrowRight className="h-4 w-4 text-slate-400" />
      </div>
      <p className="mt-2 text-sm text-slate-600">{text}</p>
    </Link>
  );
}

function InfoCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg border border-line bg-white p-5 shadow-sm">
      <h3 className="font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
    </div>
  );
}
