import AlertRow from "./AlertRow";
import { SEVERITY_STYLES } from "../format";

export default function RawTable({ alerts, loading }) {
  if (loading && alerts.length === 0) {
    return <p className="text-text-muted font-mono text-sm py-8 text-center">Loading raw stream…</p>;
  }
  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="hidden sm:flex items-center gap-3 px-4 py-2 border-b border-border font-mono text-[11px] uppercase tracking-widest text-text-muted">
        <span className="w-[68px]">time</span>
        <span className="w-16">severity</span>
        <span className="w-36">service</span>
        <span className="flex-1">message</span>
      </div>
      <div className="max-h-[560px] overflow-y-auto scrollbar-thin divide-y divide-border/50 px-4">
        {alerts.map((alert) => (
          <AlertRow
            key={alert.id}
            alert={alert}
            accentColor={SEVERITY_STYLES[alert.severity]?.color}
          />
        ))}
      </div>
      <div className="px-4 py-2 border-t border-border font-mono text-xs text-text-muted">
        {alerts.length.toLocaleString()} alerts
      </div>
    </div>
  );
}
