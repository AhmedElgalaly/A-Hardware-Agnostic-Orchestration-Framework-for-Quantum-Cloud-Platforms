import { useEffect, useMemo, useState } from "react";
import { quantumApi } from "../api/quantumApi";
import BackendTable from "../components/BackendTable";
import LoadingSpinner from "../components/LoadingSpinner";
import type { BackendCapability } from "../types/quantum";

export default function BackendsPage() {
  const [backends, setBackends] = useState<BackendCapability[]>([]);
  const [provider, setProvider] = useState("all");
  const [backendType, setBackendType] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    quantumApi.backends()
      .then(setBackends)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const providers = useMemo(() => Array.from(new Set(backends.map((backend) => backend.provider))).sort(), [backends]);
  const filtered = backends.filter((backend) => {
    const matchesProvider = provider === "all" || backend.provider === provider;
    const matchesType = backendType === "all" || backend.backend_type === backendType;
    const matchesSearch = backend.backend_name.toLowerCase().includes(search.toLowerCase());
    return matchesProvider && matchesType && matchesSearch;
  });

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-bold text-ink">Available backends</h1>
        <p className="mt-2 text-sm text-slate-600">Backends are discovered by provider adapters. Tokens are never shown here.</p>
      </header>

      <section className="grid gap-4 rounded-lg border border-line bg-white p-4 shadow-sm md:grid-cols-3">
        <label>
          <span className="label">Provider</span>
          <select className="input mt-2" value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option value="all">all</option>
            {providers.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label>
          <span className="label">Backend type</span>
          <select className="input mt-2" value={backendType} onChange={(event) => setBackendType(event.target.value)}>
            <option value="all">all</option>
            <option value="simulator">simulator</option>
            <option value="hardware">hardware</option>
          </select>
        </label>
        <label>
          <span className="label">Search backend name</span>
          <input className="input mt-2" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="aer_simulator" />
        </label>
      </section>

      {loading && <LoadingSpinner label="Loading backends" />}
      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}
      {!loading && !error && <BackendTable backends={filtered} />}
    </div>
  );
}
