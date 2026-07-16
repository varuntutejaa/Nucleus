import { useState } from "react";
import { formatDuration } from "../format";
import AlertRow from "./AlertRow";

export default function ClusterCard({ cluster }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 pt-3 pb-2 border-b border-border">
        <span className="font-mono text-xs text-text-muted">{cluster.cluster_id}</span>
        <span className="font-mono text-xs text-resolved">{cluster.size} alerts</span>
        <span className="font-mono text-xs text-text-muted">
          span {formatDuration(cluster.time_span_seconds)}
        </span>
        <span className="font-mono text-xs text-muted-status">
          {cluster.suppressed.length} suppressed
        </span>
      </div>

      <div className="px-4 py-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="h-1.5 w-1.5 rounded-full bg-signal" aria-hidden="true" />
          <span className="text-[11px] uppercase tracking-widest text-signal font-mono">
            Root cause
          </span>
        </div>
        <AlertRow alert={cluster.root_cause} accentColor="var(--color-signal)" />
        <p className="text-xs text-text-muted italic mt-1 pl-3">{cluster.explanation}</p>
      </div>

      {cluster.suppressed.length > 0 && (
        <div className="border-t border-border">
          <button
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="w-full flex items-center justify-between px-4 py-2 text-xs font-mono text-text-secondary hover:text-text hover:bg-surface-raised transition-colors"
          >
            <span>
              {expanded ? "Hide" : "Show"} {cluster.suppressed.length} suppressed alert
              {cluster.suppressed.length === 1 ? "" : "s"}
            </span>
            <span aria-hidden="true">{expanded ? "−" : "+"}</span>
          </button>
          {expanded && (
            <div className="px-4 pb-3 max-h-72 overflow-y-auto scrollbar-thin divide-y divide-border/50">
              {cluster.suppressed.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  accentColor="var(--color-muted-status)"
                  dense
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
