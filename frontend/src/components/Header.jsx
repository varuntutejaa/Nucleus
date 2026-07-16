export default function Header({ backendOk }) {
  return (
    <header className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-md bg-signal-soft flex items-center justify-center">
            <span className="h-3 w-3 rounded-full bg-signal" aria-hidden="true" />
          </div>
          <div className="leading-tight">
            <h1 className="font-semibold tracking-tight text-text text-lg">NUCLEUS</h1>
            <p className="text-[11px] uppercase tracking-widest text-text-muted font-mono">
              Alert Correlation Engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-text-secondary">
          <span
            className={`h-2 w-2 rounded-full ${
              backendOk ? "bg-resolved animate-pulse" : "bg-signal"
            }`}
            aria-hidden="true"
          />
          <span>{backendOk ? "LIVE" : "DISCONNECTED"}</span>
        </div>
      </div>
    </header>
  );
}
