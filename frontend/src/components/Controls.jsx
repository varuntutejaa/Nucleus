import { useEffect, useRef, useState } from "react";

const DEBOUNCE_MS = 300;

function WeightSlider({ label, keyName, value, onChange, accent }) {
  return (
    <div className="flex-1 min-w-[160px]">
      <div className="flex justify-between items-baseline mb-1">
        <label htmlFor={`weight-${keyName}`} className="text-xs font-mono text-text-secondary">
          {label}
        </label>
        <span className="text-xs font-mono tabular-nums" style={{ color: accent }}>
          {value.toFixed(2)}
        </span>
      </div>
      <input
        id={`weight-${keyName}`}
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={value}
        onChange={(e) => onChange(keyName, parseFloat(e.target.value))}
        className="w-full accent-signal cursor-pointer"
        style={{ accentColor: accent }}
      />
    </div>
  );
}

export default function Controls({
  view,
  onViewChange,
  weights,
  onWeightsChange,
  source,
  onSourceChange,
  replay,
}) {
  const [local, setLocal] = useState(weights);
  const timeoutRef = useRef(null);

  useEffect(() => setLocal(weights), [weights]);

  function handleChange(key, value) {
    const next = { ...local, [key]: value };
    setLocal(next);
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => onWeightsChange(next), DEBOUNCE_MS);
  }

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 pb-4">
      <div className="rounded-lg border border-border bg-surface p-4 flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div
            role="tablist"
            aria-label="View"
            className="inline-flex rounded-md border border-border-strong overflow-hidden"
          >
            {[
              { id: "correlated", label: "Correlated View" },
              { id: "raw", label: "Raw Stream" },
            ].map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={view === tab.id}
                onClick={() => onViewChange(tab.id)}
                className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                  view === tab.id
                    ? "bg-resolved-soft text-resolved"
                    : "text-text-secondary hover:text-text"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <label className="text-xs font-mono text-text-secondary">
              source
              <select
                value={source}
                onChange={(e) => onSourceChange(e.target.value)}
                className="ml-2 bg-surface-raised border border-border-strong rounded px-2 py-1 text-xs text-text"
              >
                <option value="synthetic">synthetic</option>
                <option value="dataset">dataset (loghub)</option>
              </select>
            </label>

            <button
              onClick={replay.onToggle}
              className={`px-3 py-1.5 rounded text-xs font-mono font-medium border transition-colors ${
                replay.isPlaying
                  ? "border-signal text-signal bg-signal-soft"
                  : "border-border-strong text-text-secondary hover:text-text"
              }`}
            >
              {replay.isPlaying ? "■ Stop Replay" : "▶ Replay Incident"}
            </button>
          </div>
        </div>

        {replay.isPlaying && (
          <div className="h-1 w-full rounded bg-surface-raised overflow-hidden">
            <div
              className="h-full bg-signal transition-all"
              style={{ width: `${replay.progressPct}%`, transitionDuration: "250ms" }}
            />
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-4">
          <WeightSlider
            label="alpha · semantic"
            keyName="alpha"
            value={local.alpha}
            onChange={handleChange}
            accent="var(--color-signal)"
          />
          <WeightSlider
            label="beta · temporal"
            keyName="beta"
            value={local.beta}
            onChange={handleChange}
            accent="var(--color-resolved)"
          />
          <WeightSlider
            label="gamma · service topology"
            keyName="gamma"
            value={local.gamma}
            onChange={handleChange}
            accent="var(--color-muted-status)"
          />
        </div>
      </div>
    </section>
  );
}
