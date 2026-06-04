import type { BackendCapability } from "../types/quantum";
import StatusBadge from "./StatusBadge";

export default function BackendTable({ backends }: { backends: BackendCapability[] }) {
  if (backends.length === 0) {
    return <div className="rounded-lg border border-line bg-white p-6 text-sm text-slate-600">No backends match the current filters.</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-line text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Backend</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Qubits</th>
              <th className="px-4 py-3">Native gates</th>
              <th className="px-4 py-3">Topology</th>
              <th className="px-4 py-3">Noise model</th>
              <th className="px-4 py-3">Latency ms</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {backends.map((backend) => (
              <tr key={`${backend.provider}-${backend.backend_name}`}>
                <td className="px-4 py-3 font-medium">{backend.provider}</td>
                <td className="px-4 py-3">{backend.backend_name}</td>
                <td className="px-4 py-3"><StatusBadge status={backend.backend_type} /></td>
                <td className="px-4 py-3">{backend.num_qubits}</td>
                <td className="max-w-xs px-4 py-3 text-slate-600">{backend.native_gates.join(", ") || "n/a"}</td>
                <td className="px-4 py-3">{backend.topology}</td>
                <td className="px-4 py-3">{backend.noise_model_available ? "available" : "not available"}</td>
                <td className="px-4 py-3">{backend.estimated_latency_ms}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
