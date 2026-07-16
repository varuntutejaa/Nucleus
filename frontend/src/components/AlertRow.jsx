import { formatTime, SEVERITY_STYLES } from "../format";

export default function AlertRow({ alert, accentColor, dense }) {
  const sev = SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.info;
  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-3 border-l-2 pl-3 ${
        dense ? "py-1.5" : "py-2"
      }`}
      style={{ borderColor: accentColor ?? "transparent" }}
    >
      <div className="flex items-center gap-3 sm:contents">
        <span className="font-mono text-xs text-text-muted whitespace-nowrap sm:pt-0.5">
          {formatTime(alert.timestamp)}
        </span>
        <span
          className="font-mono text-[10px] font-semibold whitespace-nowrap sm:pt-0.5 sm:w-16 sm:shrink-0"
          style={{ color: sev.color }}
        >
          {sev.label}
        </span>
        <span className="font-mono text-xs text-text-secondary whitespace-nowrap sm:pt-0.5 sm:w-36 sm:shrink-0 truncate">
          {alert.service}
        </span>
      </div>
      <span className="text-sm text-text sm:flex-1 min-w-0 break-words">{alert.message}</span>
    </div>
  );
}
