type CountsChartProps = {
  counts: Record<string, number>;
};

export default function CountsChart({ counts }: CountsChartProps) {
  const entries = Object.entries(counts);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  if (entries.length === 0) {
    return <p className="text-sm text-slate-500">No counts returned.</p>;
  }

  return (
    <div className="space-y-2">
      {entries.map(([state, value]) => (
        <div key={state} className="grid grid-cols-[4rem_1fr_4rem] items-center gap-3 text-sm">
          <span className="font-mono text-slate-700">{state}</span>
          <div className="h-6 overflow-hidden rounded bg-slate-100">
            <div className="h-full rounded bg-quantum" style={{ width: `${Math.max((value / max) * 100, 3)}%` }} />
          </div>
          <span className="text-right tabular-nums text-slate-600">{value}</span>
        </div>
      ))}
    </div>
  );
}
