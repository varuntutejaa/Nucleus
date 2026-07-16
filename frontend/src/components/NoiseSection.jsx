import { useState } from "react";
import AlertRow from "./AlertRow";

export default function NoiseSection({ noise }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-raised transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-noise" aria-hidden="true" />
          <span className="text-[11px] uppercase tracking-widest text-noise font-mono">
            Standalone alerts &mdash; unclustered, not suppressed
          </span>
          <span className="font-mono text-xs text-text-muted">({noise.length})</span>
        </div>
        <span aria-hidden="true" className="text-text-secondary">
          {expanded ? "−" : "+"}
        </span>
      </button>
      <p className="px-4 pb-2 text-xs text-text-muted -mt-1">
        HDBSCAN could not confidently group these with any incident. They are never dropped
        from view — inspect them here.
      </p>
      {expanded && (
        <div className="px-4 pb-3 max-h-96 overflow-y-auto scrollbar-thin divide-y divide-border/50 border-t border-border">
          {noise.map((alert) => (
            <AlertRow key={alert.id} alert={alert} accentColor="var(--color-noise)" dense />
          ))}
        </div>
      )}
    </div>
  );
}
