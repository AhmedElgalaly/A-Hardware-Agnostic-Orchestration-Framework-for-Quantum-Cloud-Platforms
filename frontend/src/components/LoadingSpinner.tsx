export default function LoadingSpinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-600">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-quantum" />
      <span>{label}</span>
    </div>
  );
}
