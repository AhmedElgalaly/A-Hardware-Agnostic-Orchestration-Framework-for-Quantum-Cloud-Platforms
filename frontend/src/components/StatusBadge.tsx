type StatusBadgeProps = {
  status?: string | null;
};

const styles: Record<string, string> = {
  ok: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  running: "bg-sky-50 text-sky-700 ring-sky-200",
  pending: "bg-amber-50 text-amber-700 ring-amber-200",
  partial: "bg-orange-50 text-orange-700 ring-orange-200",
  failed: "bg-rose-50 text-rose-700 ring-rose-200",
  hardware: "bg-violet-50 text-violet-700 ring-violet-200",
  simulator: "bg-cyan-50 text-cyan-700 ring-cyan-200"
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const label = status ?? "unknown";
  const className = styles[label] ?? "bg-slate-50 text-slate-700 ring-slate-200";

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${className}`}>
      {label}
    </span>
  );
}
