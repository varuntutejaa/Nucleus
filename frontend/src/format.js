export function formatDuration(seconds) {
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  if (m < 60) return rem ? `${m}m ${rem}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  return remM ? `${h}h ${remM}m` : `${h}h`;
}

export function formatTime(isoOrUnix) {
  const date =
    typeof isoOrUnix === "number" ? new Date(isoOrUnix * 1000) : new Date(isoOrUnix);
  return date.toLocaleTimeString([], { hour12: false });
}

export const SEVERITY_STYLES = {
  critical: { color: "var(--color-signal)", label: "CRITICAL" },
  warning: { color: "#d99a2b", label: "WARNING" },
  info: { color: "var(--color-text-muted)", label: "INFO" },
};
