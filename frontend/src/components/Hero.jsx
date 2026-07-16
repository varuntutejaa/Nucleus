import { useAnimatedNumber } from "../hooks/useAnimatedNumber";
import PulseCompression from "./PulseCompression";

function StatTile({ label, value, accent, suffix }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3 flex-1 min-w-[120px]">
      <div className="text-[11px] uppercase tracking-widest text-text-muted font-mono mb-1">
        {label}
      </div>
      <div
        className="text-2xl sm:text-3xl font-semibold font-mono tabular-nums"
        style={{ color: accent }}
      >
        {value}
        {suffix && <span className="text-base text-text-muted ml-1">{suffix}</span>}
      </div>
    </div>
  );
}

export default function Hero({ metrics, loading }) {
  const rawCount = useAnimatedNumber(metrics?.raw_count ?? 0);
  const clusterCount = useAnimatedNumber(metrics?.cluster_count ?? 0);
  const noiseCount = useAnimatedNumber(metrics?.noise_count ?? 0);
  const reduction = useAnimatedNumber(Math.round(metrics?.reduction_pct ?? 0));

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 pt-8 pb-6">
      <div className="flex flex-col lg:flex-row gap-6 items-stretch">
        <div className="flex-1 flex flex-col justify-center">
          <p className="font-mono text-xs uppercase tracking-widest text-signal mb-2">
            Incident correlation, live
          </p>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-text mb-3">
            {rawCount.toLocaleString()} raw alerts{" "}
            <span className="text-text-muted">&rarr;</span>{" "}
            <span className="text-resolved">{clusterCount}</span> clusters
          </h2>
          <p className="text-text-secondary max-w-xl mb-5">
            Nucleus groups temporally and semantically related alerts, calls out the
            most likely root cause per incident, and keeps every suppressed or
            standalone alert one click away.
          </p>
          <div className="flex flex-wrap gap-3">
            <StatTile label="Raw Alerts" value={rawCount.toLocaleString()} accent="var(--color-text)" />
            <StatTile label="Clusters" value={clusterCount} accent="var(--color-resolved)" />
            <StatTile label="Standalone" value={noiseCount} accent="var(--color-noise)" />
            <StatTile label="Reduction" value={reduction} suffix="%" accent="var(--color-signal)" />
          </div>
        </div>

        <div className="lg:w-[420px] flex flex-col justify-center gap-2">
          <PulseCompression
            clusterCount={metrics?.cluster_count ?? 1}
            noiseCount={metrics?.noise_count ?? 0}
            rawCount={metrics?.raw_count ?? 0}
          />
          <p className="text-[11px] text-text-muted font-mono text-center">
            {loading ? "recomputing…" : "sampled visualization, not to scale"}
          </p>
        </div>
      </div>
    </section>
  );
}
