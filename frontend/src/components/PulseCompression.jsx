import { useMemo } from "react";

const SAMPLE_SIZE = 60;
const SEVERITY_COLORS = ["var(--color-signal)", "var(--color-muted-status)", "var(--color-text-muted)"];

// Deterministic pseudo-random in [0,1) so the scattered layout is stable
// across re-renders (only regenerated when the sample size changes).
function seeded(i, salt) {
  const x = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * The hero's signature moment: a cloud of dots representing raw alerts
 * visibly collapses into a handful of cluster markers, while a separate
 * subset of "noise" dots stays scattered -- reinforcing that unclustered
 * alerts are never silently dropped, just left standalone.
 */
export default function PulseCompression({ clusterCount, noiseCount, rawCount }) {
  const clusterBoundFraction =
    rawCount > 0 ? Math.max(0, (rawCount - noiseCount) / rawCount) : 0.7;
  const clusterDotCount = Math.round(SAMPLE_SIZE * clusterBoundFraction);
  const targetCount = Math.max(clusterCount, 1);

  const scatterDots = useMemo(
    () =>
      Array.from({ length: SAMPLE_SIZE }, (_, i) => ({
        id: i,
        x: 6 + seeded(i, 1) * 88,
        y: 8 + seeded(i, 2) * 62,
        color: SEVERITY_COLORS[i % SEVERITY_COLORS.length],
      })),
    [],
  );

  const targets = useMemo(
    () =>
      Array.from({ length: targetCount }, (_, i) => ({
        x: targetCount === 1 ? 50 : 8 + (i / (targetCount - 1)) * 84,
        y: 78,
      })),
    [targetCount],
  );

  return (
    <div
      className="relative h-40 sm:h-48 w-full overflow-hidden rounded-lg border border-border bg-surface/60"
      aria-hidden="true"
    >
      <div className="absolute inset-x-0 top-1 text-center text-[10px] uppercase tracking-widest text-text-muted font-mono">
        raw alerts
      </div>
      <div className="absolute inset-x-0 bottom-1 text-center text-[10px] uppercase tracking-widest text-text-muted font-mono">
        correlated clusters
      </div>

      {scatterDots.map((dot, i) => {
        const isClusterBound = i < clusterDotCount;
        const target = isClusterBound ? targets[i % targets.length] : null;
        const left = target ? target.x : dot.x;
        const top = target ? target.y : dot.y;
        return (
          <span
            key={dot.id}
            className="absolute rounded-full transition-all ease-out"
            style={{
              left: `${left}%`,
              top: `${top}%`,
              width: isClusterBound ? 5 : 4,
              height: isClusterBound ? 5 : 4,
              background: isClusterBound ? "var(--color-resolved)" : "var(--color-noise)",
              opacity: isClusterBound ? 0.9 : 0.55,
              transitionDuration: "900ms",
              transitionDelay: `${(i % 20) * 20}ms`,
              transform: "translate(-50%, -50%)",
            }}
          />
        );
      })}

      {targets.map((t, i) => (
        <span
          key={`marker-${i}`}
          className="absolute rounded-full border-2 border-resolved"
          style={{
            left: `${t.x}%`,
            top: `${t.y}%`,
            width: 14,
            height: 14,
            transform: "translate(-50%, -50%)",
            boxShadow: "0 0 12px var(--color-resolved-soft)",
          }}
        />
      ))}
    </div>
  );
}
